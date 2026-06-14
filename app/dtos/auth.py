from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.validators import validate_birthday, validate_password, validate_phone_number
from app.models.users import Gender


class SignUpRequest(BaseModel):
    email: Annotated[
        EmailStr,
        Field(None, max_length=40),
    ]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    name: Annotated[str, Field(max_length=20)]
    nickname: Annotated[str, Field(min_length=2, max_length=10)]
    gender: Gender
    birth_date: Annotated[date, AfterValidator(validate_birthday)]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]


class FindIdRequest(BaseModel):
    name: Annotated[str, Field(max_length=20)]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]


class FindIdResponse(BaseModel):
    masked_email: str
    created_at: date


class PreviousAccountResponse(BaseModel):
    """탈퇴 계정 감지(복구 가능 여부). 인증 전이므로 최소 정보만 — 상세 통계는 복구(인증) 단계에서."""

    masked_email: str
    deleted_at: datetime
    restore_deadline: datetime


class RestoreRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=40)]


class DestroyRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=40)]


class ResetPasswordRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=40)]
    name: Annotated[str, Field(min_length=1, max_length=20)]
    new_password: Annotated[str, Field(min_length=8, max_length=64), AfterValidator(validate_password)]


class RestoredAccountResponse(BaseModel):
    """복구 완료 응답. 이메일 인증을 마친 본인이므로 상세 통계 포함."""

    email: EmailStr
    created_at: datetime
    deleted_at: datetime
    challenge_count: int
    points: int
    pet_name: str | None = None


class SendVerificationRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=40)]
    # 비밀번호 찾기 흐름에서만 전달. 주어지면 email+name 일치 계정에만 메일을 보낸다.
    # (가입 흐름은 name 없이 호출 — 기존 동작 유지)
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=20)] = None


class VerifyEmailRequest(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=128)]


class VerifyEmailResponse(BaseModel):
    email: EmailStr
    verified: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse): ...
