from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.validators import optional_after_validator, validate_phone_number
from app.dtos.base import BaseSerializerModel
from app.models.users import Gender


class UserUpdateRequest(BaseModel):
    """마이페이지 프로필 수정. 사양상 닉네임/휴대폰/아바타만 변경 가능."""

    nickname: Annotated[str | None, Field(None, min_length=2, max_length=10)]
    phone_number: Annotated[
        str | None,
        Field(None, description="Available Format: +8201011112222, 01011112222, 010-1111-2222"),
        optional_after_validator(validate_phone_number),
    ]
    avatar_file_id: Annotated[int | None, Field(None, description="files API 로 업로드한 PROFILE_IMAGE id")]


class PasswordChangeRequest(BaseModel):
    current_password: Annotated[str, Field(min_length=8, max_length=64)]
    new_password: Annotated[str, Field(min_length=8, max_length=64)]


class WithdrawRequest(BaseModel):
    """회원 탈퇴 요청. 탈퇴 이유는 선택(프론트 탈퇴 폼에서 선택/작성)."""

    reason: Annotated[str | None, Field(None, max_length=500)]


class UserInfoResponse(BaseSerializerModel):
    id: UUID
    email: str
    name: str
    nickname: str | None = None
    phone_number: str
    birthday: date
    gender: Gender
    avatar_file_id: int | None = None
    avatar_url: str | None = None
    created_at: datetime
