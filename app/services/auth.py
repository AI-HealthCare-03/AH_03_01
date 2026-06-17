import logging
from datetime import datetime, timedelta

from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.transactions import in_transaction

from app.core import config
from app.core.jwt.tokens import AccessToken, RefreshToken
from app.core.utils.common import normalize_phone_number
from app.core.utils.security import hash_password, verify_password
from app.dtos.auth import (
    FindIdRequest,
    FindIdResponse,
    LoginRequest,
    PreviousAccountResponse,
    RestoredAccountResponse,
    SignUpRequest,
)
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.email_verification import EmailVerificationService
from app.services.jwt import JwtService

# 탈퇴(soft delete) 후 개인정보 보관 기간. 이 기간 내에는 복구 가능, 경과 시 파기(개인정보처리방침 기준).
ACCOUNT_RETENTION_DAYS = 30

# 로그인 연속 실패 잠금 정책 — 임계 도달 시 이메일 인증으로만 해제.
LOGIN_FAIL_LOCK_THRESHOLD = 5
ACCOUNT_LOCKED_DETAIL = "로그인 5회 실패로 계정이 잠겼습니다. 이메일 인증으로 잠금을 해제해 주세요."
# 잠금 임박 경고 노출 임계: 남은 시도가 이 값 이하일 때만 잔여 횟수를 안내한다.
# (평소·미존재 이메일은 일반 메시지 유지 → 계정 열거 노출을 잠금 임박 구간으로 한정)
LOGIN_FAIL_WARN_REMAINING = 2

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()
        self.email_verification = EmailVerificationService()

    async def signup(self, data: SignUpRequest) -> User:
        # 이메일 중복 체크
        await self.check_email_exists(data.email)

        # 닉네임 중복 체크
        await self.check_nickname_exists(data.nickname)

        # 이메일 본인 인증 확인 (미인증 시 가입 차단)
        if not await self.email_verification.is_verified(str(data.email)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 본인 인증이 필요합니다.")

        # 입력받은 휴대폰 번호를 노말라이즈
        normalized_phone_number = normalize_phone_number(data.phone_number)

        # 휴대폰 번호 중복 체크
        await self.check_phone_number_exists(normalized_phone_number)

        # 유저 생성
        async with in_transaction():
            user = await self.user_repo.create_user(
                email=data.email,
                hashed_password=hash_password(data.password),  # 해시화된 비밀번호를 사용
                name=data.name,
                nickname=data.nickname,
                phone_number=normalized_phone_number,
                gender=data.gender,
                birthday=data.birth_date,
            )

        # 가입 성공 후 인증 완료 플래그 소비 (재사용 방지)
        await self.email_verification.consume(str(data.email))
        return user

    async def authenticate(self, data: LoginRequest) -> User:
        # 이메일로 사용자 조회
        email = str(data.email)
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 로그인 연속 실패 잠금: 임계 도달 시 비밀번호 검증 전에 차단하고 이메일 인증 해제로 안내.
        if user.login_fail_count >= LOGIN_FAIL_LOCK_THRESHOLD:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=ACCOUNT_LOCKED_DETAIL)

        # 비밀번호 검증
        if not verify_password(data.password, user.hashed_password):
            await self.user_repo.increment_login_fail(user.id)
            new_fail_count = user.login_fail_count + 1
            # 이번 실패로 임계 도달 시 잠금 안내.
            if new_fail_count >= LOGIN_FAIL_LOCK_THRESHOLD:
                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=ACCOUNT_LOCKED_DETAIL)
            # 잠금 임박(남은 시도 ≤ 임계) 시에만 잔여 횟수 경고. 그 외엔 일반 메시지로 계정 열거 방지.
            remaining = LOGIN_FAIL_LOCK_THRESHOLD - new_fail_count
            if remaining <= LOGIN_FAIL_WARN_REMAINING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"비밀번호가 올바르지 않습니다. {remaining}회 더 실패하면 계정이 잠깁니다.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 활성 사용자 체크
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")

        # 로그인 성공 — 누적 실패 카운트 초기화.
        if user.login_fail_count:
            await self.user_repo.reset_login_fail(user.id)

        return user

    async def find_id(self, data: FindIdRequest) -> FindIdResponse:
        # 가입 시 노말라이즈된 형태로 저장되므로 동일하게 정규화 후 조회
        normalized_phone_number = normalize_phone_number(data.phone_number)
        user = await self.user_repo.get_user_by_name_and_phone(data.name, normalized_phone_number)

        # 계정 열거(account enumeration) 방어: 미일치 시 동일한 404 응답
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일치하는 계정을 찾을 수 없습니다.")

        return FindIdResponse(masked_email=self._mask_email(user.email), created_at=user.created_at.date())

    async def get_previous_account(self, email: str) -> PreviousAccountResponse:
        """이메일로 복구 가능한 탈퇴 계정을 감지. 인증 전이므로 마스킹 이메일·탈퇴일·복구마감만 반환.

        상세 통계(챌린지·포인트·펫)는 복구(이메일 인증) 단계에서 제공한다.
        """
        user = await self.user_repo.get_deleted_by_email(email)
        if user is None or user.deleted_at is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="복구 가능한 탈퇴 계정이 없습니다.")

        deadline = user.deleted_at + timedelta(days=ACCOUNT_RETENTION_DAYS)
        if deadline <= datetime.now(config.TIMEZONE):
            # 보관 기간 경과 — 곧 파기되거나 파기됨, 복구 불가
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="복구 가능한 탈퇴 계정이 없습니다.")

        return PreviousAccountResponse(
            masked_email=self._mask_email(user.email),
            deleted_at=user.deleted_at,
            restore_deadline=deadline,
        )

    async def restore_account(self, email: str) -> RestoredAccountResponse:
        """이메일 본인 인증을 마친 사용자의 탈퇴 계정을 복구(is_deleted=false)한다.

        보관 기간 내 탈퇴 계정만 복구 가능. 인증 완료자에게만 상세 통계를 반환한다.
        """
        if not await self.email_verification.is_verified(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 본인 인증이 필요합니다.")

        user = await self.user_repo.get_deleted_by_email(email)
        if user is None or user.deleted_at is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="복구 가능한 탈퇴 계정이 없습니다.")
        if user.deleted_at + timedelta(days=ACCOUNT_RETENTION_DAYS) <= datetime.now(config.TIMEZONE):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="복구 가능한 탈퇴 계정이 없습니다.")
        if user.is_banned:  # 운영자 제재(ban) 우회 방지 — get_request_user 와 동일하게 정지 계정은 하드 차단
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="정지된 계정은 복구할 수 없습니다.")

        prev_deleted_at = user.deleted_at
        user.is_deleted = False
        user.is_active = True
        user.deleted_at = None  # type: ignore[assignment]  # null=True 필드(스텁은 datetime)
        user.withdrawal_reason = None  # type: ignore[assignment]  # null=True 필드(스텁은 str)
        async with in_transaction():
            await user.save(update_fields=["is_deleted", "is_active", "deleted_at", "withdrawal_reason", "updated_at"])
        await self.email_verification.consume(email)

        try:
            stats = await self._account_stats(user.id)
        except Exception:  # noqa: BLE001  # 부가 통계 실패가 이미 커밋된 복구를 500 으로 깨뜨리지 않도록 폴백
            stats = {"challenge_count": 0, "points": 0, "pet_name": None}
        return RestoredAccountResponse(
            email=user.email,
            created_at=user.created_at,
            deleted_at=prev_deleted_at,
            challenge_count=stats["challenge_count"],
            points=stats["points"],
            pet_name=stats["pet_name"],
        )

    async def destroy_previous_account(self, email: str) -> None:
        """이메일 본인 인증을 마친 사용자의 탈퇴 계정을 즉시 영구 파기(하드 삭제)한다.

        '새로 시작하기' — 30일 보관 기간을 기다리지 않고 본인 요청으로 파기.
        DB cascade 로 PII/PHI 동반 삭제(챌린지는 creator SET_NULL 로 보존).
        """
        if not await self.email_verification.is_verified(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 본인 인증이 필요합니다.")

        user = await self.user_repo.get_deleted_by_email(email)
        if user is None or user.deleted_at is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파기할 탈퇴 계정이 없습니다.")
        if user.is_banned:  # 정지 계정은 본인 파기로 자료 인멸 못 하게 차단(운영/조사 보존)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="정지된 계정은 파기할 수 없습니다.")

        async with in_transaction():
            await user.delete()
        await self.email_verification.consume(email)
        # 감사 추적: 비가역 영구 파기 — PII 마스킹(이메일)하여 기록.
        logger.info("탈퇴 계정 영구 파기 user_id=%s email=%s", user.id, self._mask_email(email))

    async def reset_password(self, email: str, name: str, new_password: str) -> None:
        """이메일 본인 인증을 마친 사용자가 새 비밀번호를 설정한다(비밀번호 찾기).

        email+name 으로 계정을 식별하고, 새 비밀번호가 기존과 같으면 거부한다.
        """
        if not await self.email_verification.is_verified(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 본인 인증이 필요합니다.")

        user = await self.user_repo.get_user_by_email(email)
        if user is None or user.is_deleted or user.name != name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일치하는 계정을 찾을 수 없습니다.")

        if verify_password(new_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용한 번호입니다.")

        user.hashed_password = hash_password(new_password)
        async with in_transaction():
            await user.save(update_fields=["hashed_password", "updated_at"])
        await self.email_verification.consume(email)
        # 감사 추적: 비밀번호 재설정 — PII 마스킹(이메일)하여 기록.
        logger.info("비밀번호 재설정 user_id=%s email=%s", user.id, self._mask_email(email))

    async def unlock_account(self, email: str, name: str) -> None:
        """로그인 연속 실패로 잠긴 계정을 이메일 본인 인증 후 해제(실패 카운트 초기화).

        비밀번호 재설정과 동일하게 email 본인 인증 + email/name 일치로 계정을 식별한다.
        """
        if not await self.email_verification.is_verified(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 본인 인증이 필요합니다.")

        user = await self.user_repo.get_user_by_email(email)
        if user is None or user.is_deleted or user.name != name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일치하는 계정을 찾을 수 없습니다.")

        await self.user_repo.reset_login_fail(user.id)
        await self.email_verification.consume(email)
        # 감사 추적: 계정 잠금 해제 — PII 마스킹(이메일)하여 기록.
        logger.info("계정 잠금 해제 user_id=%s email=%s", user.id, self._mask_email(email))

    @staticmethod
    async def _account_stats(user_id: object) -> dict:
        """복구 계정의 요약 통계(챌린지 수·포인트·펫 이름). 순환 import 방지 위해 지연 import."""
        from app.models.challenge import ChallengeParticipant, ParticipantStatus  # noqa: PLC0415
        from app.repositories.pet_repository import PetRepository  # noqa: PLC0415
        from app.services.pet import PointService  # noqa: PLC0415

        points = await PointService().balance(user_id)  # type: ignore[arg-type]  # UUID PK (스텁 int)
        pet = await PetRepository().get_by_user(user_id)  # type: ignore[arg-type]
        challenge_count = await ChallengeParticipant.filter(user_id=user_id, status=ParticipantStatus.APPROVED).count()
        return {"challenge_count": challenge_count, "points": points, "pet_name": pet.name if pet else None}

    @staticmethod
    def _mask_email(email: str) -> str:
        """이메일 로컬파트를 처음/끝 1글자만 남기고 마스킹. 예: jkh3043@gmail.com -> j*****3@gmail.com"""
        local, _, domain = email.partition("@")
        if not domain:
            return email
        if len(local) <= 2:
            return f"{local[0]}*@{domain}"
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked}@{domain}"

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        await self.user_repo.update_last_login(user.id)
        return self.jwt_service.issue_jwt_pair(user)

    async def check_email_exists(self, email: str | EmailStr) -> None:
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_nickname_exists(self, nickname: str) -> None:
        if await self.user_repo.exists_by_nickname(nickname):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 닉네임입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")
