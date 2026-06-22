from datetime import date, datetime
from typing import Annotated, Literal

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
    # 소셜(카카오) 계정은 이메일이 없으므로 masked_email 은 None 이고 social_provider 로 안내한다.
    masked_email: str | None = None
    social_provider: str | None = None
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


class UnlockAccountRequest(BaseModel):
    """로그인 5회 실패 잠금 해제 — 이메일 본인 인증 + email/name 일치 필요(비밀번호 재설정과 동일 패턴)."""

    email: Annotated[EmailStr, Field(max_length=40)]
    name: Annotated[str, Field(min_length=1, max_length=20)]


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
    # 인증 완료 플래그를 격리할 네임스페이스(예: "password_change"). 미지정 시 기존 공유 키.
    purpose: Annotated[str | None, Field(default=None, max_length=40)] = None


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


# ─── 카카오 소셜 로그인/가입 ────────────────────────────────────────


class KakaoAuthorizeUrlResponse(BaseModel):
    authorize_url: str
    state: str


class KakaoCallbackRequest(BaseModel):
    code: Annotated[str, Field(min_length=1)]
    state: Annotated[str, Field(min_length=1)]


class KakaoPrefill(BaseModel):
    # 소셜 계정은 이메일을 수집하지 않으므로 prefill 은 닉네임만 제공한다.
    nickname: str | None = None


class KakaoCallbackResponse(BaseModel):
    """콜백 결과.

    - status=login: access_token
    - status=signup_required: signup_ticket + prefill
    - status=restore_required: 탈퇴 계정 발견 — restore_ticket + 마스킹 이메일·탈퇴일·복구마감
      (카카오 신원으로 이미 본인 확인을 마쳤으므로 별도 이메일 인증 없이 복구/파기를 선택한다)
    """

    status: Literal["login", "signup_required", "restore_required"]
    access_token: str | None = None
    signup_ticket: str | None = None
    prefill: KakaoPrefill | None = None
    restore_ticket: str | None = None
    masked_email: str | None = None
    deleted_at: datetime | None = None
    restore_deadline: datetime | None = None


class KakaoRestoreTicketRequest(BaseModel):
    """카카오 탈퇴 계정 복구/파기 요청. restore_ticket 은 콜백에서 발급한 단기 티켓(카카오 신원 증명)."""

    restore_ticket: Annotated[str, Field(min_length=1)]


class KakaoSignupRequest(BaseModel):
    # 소셜 계정은 이메일을 수집하지 않는다(카카오가 본인인증 대행) → email 필드 없음.
    signup_ticket: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(max_length=20)]
    nickname: Annotated[str, Field(min_length=2, max_length=10)]
    gender: Gender
    birth_date: Annotated[date, AfterValidator(validate_birthday)]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]
    terms_agreed: bool
    privacy_agreed: bool
