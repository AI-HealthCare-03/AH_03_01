import logging
import time
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.core import config
from app.core.jwt.exceptions import TokenBackendError, TokenBackendExpiredError
from app.core.jwt.state import token_backend
from app.core.jwt.tokens import AccessToken, RefreshToken
from app.core.utils.common import normalize_phone_number
from app.core.utils.security import (
    generate_unusable_password,
    hash_password,
    verify_oauth_state,
    verify_password,
)
from app.dtos.auth import (
    FindIdRequest,
    FindIdResponse,
    KakaoCallbackResponse,
    KakaoPrefill,
    KakaoSignupRequest,
    LoginRequest,
    PreviousAccountResponse,
    RestoredAccountResponse,
    SignUpRequest,
)
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.email_verification import EmailVerificationService
from app.services.jwt import JwtService
from app.services.kakao_oauth import KakaoOAuthService

# 탈퇴(soft delete) 후 개인정보 보관 기간. 이 기간 내에는 복구 가능, 경과 시 파기(개인정보처리방침 기준).
ACCOUNT_RETENTION_DAYS = 30

# 로그인 연속 실패 잠금 정책 — 임계 도달 시 이메일 인증으로만 해제.
LOGIN_FAIL_LOCK_THRESHOLD = 5
ACCOUNT_LOCKED_DETAIL = "로그인 5회 실패로 계정이 잠겼습니다. 이메일 인증으로 잠금을 해제해 주세요."
# 잠금 임박 경고 노출 임계: 남은 시도가 이 값 이하일 때만 잔여 횟수를 안내한다.
# (평소·미존재 이메일은 일반 메시지 유지 → 계정 열거 노출을 잠금 임박 구간으로 한정)
LOGIN_FAIL_WARN_REMAINING = 2

# 카카오 신규 가입 티켓(JWT) 유효 시간(초). 콜백→가입 폼 작성→제출까지의 짧은 단계 전용.
KAKAO_SIGNUP_TICKET_TTL_SECONDS = 15 * 60
KAKAO_SIGNUP_TICKET_TYPE = "kakao_signup"
KAKAO_PROVIDER = "kakao"

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()
        self.email_verification = EmailVerificationService()
        self.kakao_oauth = KakaoOAuthService()

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

    async def kakao_callback(
        self, code: str, state: str
    ) -> tuple[KakaoCallbackResponse, dict[str, AccessToken | RefreshToken] | None]:
        """카카오 콜백 처리.

        기존 소셜 계정이면 로그인(access/refresh 토큰 dict 함께 반환), 신규면 가입 티켓을 발급한다.
        반환: (응답 DTO, 토큰 dict | None). 라우터가 None 이 아닐 때만 쿠키를 심는다.
        """
        if not verify_oauth_state(state):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 인증 요청입니다.")

        kakao_access_token = await self.kakao_oauth.exchange_code(code)
        profile = await self.kakao_oauth.fetch_profile(kakao_access_token)

        user = await self.user_repo.get_user_by_social(KAKAO_PROVIDER, profile.social_id)
        if user is not None:
            if user.is_banned:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="정지된 계정입니다.")
            if user.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="탈퇴한 계정입니다. 계정 복구 후 이용해 주세요.",
                )
            tokens = await self.login(user)
            response = KakaoCallbackResponse(status="login", access_token=str(tokens["access_token"]))
            return response, tokens

        # 신규 사용자 — 추가 정보 입력을 위한 단기 가입 티켓 발급.
        signup_ticket = token_backend.encode(
            {
                "type": KAKAO_SIGNUP_TICKET_TYPE,
                "provider": KAKAO_PROVIDER,
                "social_id": profile.social_id,
                "prefill": {"nickname": profile.nickname, "email": profile.email},
                "exp": int(time.time()) + KAKAO_SIGNUP_TICKET_TTL_SECONDS,
                "jti": uuid4().hex,
            }
        )
        response = KakaoCallbackResponse(
            status="signup_required",
            signup_ticket=signup_ticket,
            prefill=KakaoPrefill(nickname=profile.nickname, email=profile.email),
        )
        return response, None

    async def kakao_signup(self, data: KakaoSignupRequest) -> dict[str, AccessToken | RefreshToken]:
        """카카오 가입 티켓 + 추가 입력으로 신규 소셜 계정을 생성하고 로그인 토큰을 발급한다."""
        if not (data.terms_agreed and data.privacy_agreed):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="약관 및 개인정보 처리방침 동의가 필요합니다."
            )

        social_id = self._decode_kakao_signup_ticket(data.signup_ticket)

        # 티켓 재사용/경합 방지 + 일반 가입 중복 검증(기존 헬퍼 재사용).
        if await self.user_repo.get_user_by_social(KAKAO_PROVIDER, social_id) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 카카오 계정입니다.")
        await self.check_email_exists(data.email)
        await self.check_nickname_exists(data.nickname)

        normalized_phone_number = normalize_phone_number(data.phone_number)
        await self.check_phone_number_exists(normalized_phone_number)

        now = datetime.now(config.TIMEZONE)
        try:
            async with in_transaction():
                user = await self.user_repo.create_user(
                    email=data.email,
                    hashed_password=generate_unusable_password(),  # 비번 로그인 불가(소셜 전용)
                    name=data.name,
                    nickname=data.nickname,
                    phone_number=normalized_phone_number,
                    gender=data.gender,
                    birthday=data.birth_date,
                    social_provider=KAKAO_PROVIDER,
                    social_id=social_id,
                )
                user.terms_agreed_at = now
                user.privacy_agreed_at = now
                await user.save(update_fields=["terms_agreed_at", "privacy_agreed_at", "updated_at"])
        except IntegrityError as err:
            # 코드레벨 중복검사~INSERT 사이 동시 가입(TOCTOU)은 (social_provider, social_id)
            # 유니크 인덱스가 막는다. 500 대신 409 로 정리한다.
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 계정입니다.") from err

        return await self.login(user)

    @staticmethod
    def _decode_kakao_signup_ticket(ticket: str) -> str:
        """가입 티켓을 검증하고 social_id 를 반환. 만료/위조/타입불일치는 401."""
        try:
            payload = token_backend.decode(ticket)
        except TokenBackendExpiredError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="가입 세션이 만료되었습니다. 다시 시도해 주세요."
            ) from err
        except TokenBackendError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 가입 요청입니다."
            ) from err

        if payload.get("type") != KAKAO_SIGNUP_TICKET_TYPE or not payload.get("social_id"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 가입 요청입니다.")
        return str(payload["social_id"])

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
