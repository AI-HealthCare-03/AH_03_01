from datetime import datetime

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.core import config
from app.core.utils.common import normalize_phone_number
from app.core.utils.security import hash_password, verify_password
from app.dtos.users import PasswordChangeRequest, UserUpdateRequest
from app.models.files import FileType, FileUpload
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService

# 로그인 상태 비밀번호 변경 전용 이메일 인증 네임스페이스(프론트 send/check 와 동일 문자열 사용).
PASSWORD_CHANGE_PURPOSE = "password_change"


class UserManageService:
    def __init__(self):
        self.repo = UserRepository()
        self.auth_service = AuthService()

    async def update_user(self, user: User, data: UserUpdateRequest) -> User:
        payload: dict = {}
        if data.nickname is not None and data.nickname != user.nickname:
            if await self.repo.exists_by_nickname(data.nickname):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 사용중인 닉네임입니다.",
                )
            payload["nickname"] = data.nickname
        if data.phone_number is not None:
            normalized_phone_number = normalize_phone_number(data.phone_number)
            if normalized_phone_number != user.phone_number:
                await self.auth_service.check_phone_number_exists(normalized_phone_number)
            payload["phone_number"] = normalized_phone_number
        if data.avatar_file_id is not None:
            # 본인이 업로드한 PROFILE_IMAGE 인지 검증
            file_record = await FileUpload.get_or_none(
                id=data.avatar_file_id,
                uploader_id=user.id,
                file_type=FileType.PROFILE_IMAGE,
            )
            if file_record is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="유효하지 않은 프로필 이미지입니다.",
                )
            payload["avatar_file_id"] = data.avatar_file_id

        if not payload:
            return user

        async with in_transaction():
            await self.repo.update_instance(user=user, data=payload)
            await user.refresh_from_db()
        return user

    async def change_password(self, user: User, data: PasswordChangeRequest) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 일치하지 않습니다.",
            )
        if data.current_password == data.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기존과 동일한 비밀번호는 사용할 수 없습니다.",
            )
        # 로그인 상태라도 비밀번호 변경에는 이메일 본인 인증을 요구한다(세션 탈취 시 비번 변경 방어).
        # 비번 변경 전용 purpose 네임스페이스로 격리해, 가입·비번찾기 등 다른 흐름에서 남은
        # verified 플래그로 게이트가 통과되는 교차흐름 재사용을 차단한다.
        if not await self.auth_service.email_verification.is_verified(user.email, purpose=PASSWORD_CHANGE_PURPOSE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 본인 인증이 필요합니다.",
            )
        user.hashed_password = hash_password(data.new_password)
        async with in_transaction():
            await user.save(update_fields=["hashed_password", "updated_at"])
        await self.auth_service.email_verification.consume(user.email, purpose=PASSWORD_CHANGE_PURPOSE)

    async def withdraw(self, user: User, reason: str | None = None) -> None:
        """회원 탈퇴 (soft delete). is_deleted=true·deleted_at=now 로 표시하고 비활성화.

        실제 정보는 30일간 보관 후 파기(별도 잡). 보관 기간 내 재가입 시 복구 가능.
        탈퇴 즉시 로그인 세션 무효화를 위해 refresh_token_hash 도 제거한다.
        """
        if user.is_deleted:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 탈퇴한 계정입니다.")

        user.is_deleted = True
        user.is_active = False
        user.deleted_at = datetime.now(config.TIMEZONE)
        user.withdrawal_reason = reason  # type: ignore[assignment]  # null=True 필드(스텁은 str)
        user.refresh_token_hash = None  # type: ignore[assignment]  # null=True 필드(스텁은 str)
        async with in_transaction():
            await user.save(
                update_fields=[
                    "is_deleted",
                    "is_active",
                    "deleted_at",
                    "withdrawal_reason",
                    "refresh_token_hash",
                    "updated_at",
                ]
            )
