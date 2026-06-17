from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import EmailStr
from tortoise.expressions import F

from app.core import config
from app.models.users import Gender, User

ALLOWED_UPDATE_FIELDS = ["nickname", "phone_number", "avatar_file_id"]
UPDATED_AT_FIELD = "updated_at"


class UserRepository:
    def __init__(self):
        self._model = User

    async def get_all(self):
        return await self._model.all()

    async def get_user(self, user_id: UUID | str) -> User | None:
        return await self._model.get_or_none(id=user_id)

    async def create_user(
        self,
        email: str | EmailStr,
        hashed_password: str,
        name: str,
        nickname: str,
        phone_number: str,
        gender: Gender,
        birthday: date,
        *,
        is_active: bool = True,
        is_admin: bool = False,
        social_provider: str | None = None,
        social_id: str | None = None,
    ) -> User:
        return await self._model.create(
            email=email,
            hashed_password=hashed_password,
            name=name,
            nickname=nickname,
            phone_number=phone_number,
            gender=gender,
            birthday=birthday,
            is_active=is_active,
            is_admin=is_admin,
            social_provider=social_provider,
            social_id=social_id,
        )

    async def get_user_by_email(self, email: str) -> User | None:
        return await self._model.get_or_none(email=email)

    async def get_user_by_social(self, social_provider: str, social_id: str) -> User | None:
        """소셜 (provider, social_id) 로 계정을 조회. (카카오 등 소셜 로그인 식별)"""
        return await self._model.get_or_none(social_provider=social_provider, social_id=social_id)

    async def get_user_by_name_and_phone(self, name: str, phone_number: str) -> User | None:
        return await self._model.filter(name=name, phone_number=phone_number, is_deleted=False).first()

    async def get_active_user_by_email_and_name(self, email: str, name: str) -> User | None:
        """email + name 이 모두 일치하는 활성(미탈퇴) 계정을 조회. (비밀번호 찾기 본인 확인)"""
        return await self._model.filter(email=email, name=name, is_deleted=False).first()

    async def get_deleted_by_email(self, email: str) -> User | None:
        """이메일로 탈퇴(soft delete) 계정을 조회. 가장 최근 탈퇴 건."""
        return await self._model.filter(email=email, is_deleted=True).order_by("-deleted_at").first()

    async def list_purgeable(self, before: datetime, *, limit: int | None = None) -> list[User]:
        """보관 기간이 지난 탈퇴 계정(파기 대상)을 오래된 탈퇴 순으로 조회한다.

        조건: is_deleted=True AND deleted_at <= before (= now - 보관기간).
        deleted_at 이 NULL 인 비정상 row 는 대상에서 제외된다(filter 의 __lte 가 NULL 을 매치하지 않음).
        """
        query = self._model.filter(is_deleted=True, deleted_at__lte=before).order_by("deleted_at")
        if limit is not None:
            query = query.limit(limit)
        return await query

    async def exists_by_email(self, email: str) -> bool:
        return await self._model.filter(email=email).exists()

    async def exists_by_nickname(self, nickname: str) -> bool:
        return await self._model.filter(nickname=nickname).exists()

    async def exists_by_phone_number(self, phone_number: str) -> bool:
        return await self._model.filter(phone_number=phone_number).exists()

    async def update_last_login(self, user_id: UUID) -> None:
        await self._model.filter(id=user_id).update(last_login=datetime.now(config.TIMEZONE))

    async def increment_login_fail(self, user_id: UUID) -> None:
        """로그인 실패 카운트 원자적 +1 (동시 실패 경합 방지)."""
        await self._model.filter(id=user_id).update(login_fail_count=F("login_fail_count") + 1)

    async def reset_login_fail(self, user_id: UUID) -> None:
        """로그인 성공·잠금 해제 시 실패 카운트 초기화."""
        await self._model.filter(id=user_id).update(login_fail_count=0)

    async def update_instance(self, user: User, data: dict[str, Any]) -> None:
        update_fields = []
        for key, value in data.items():
            if value is not None:
                setattr(user, key, value)
                update_fields.append(key)
        if update_fields:
            user.updated_at = datetime.now(config.TIMEZONE)
            update_fields.append(UPDATED_AT_FIELD)
            await user.save(update_fields=update_fields)
