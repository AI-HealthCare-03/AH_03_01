from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.core.limiter import limiter
from app.dtos.auth import (
    DestroyRequest,
    FindIdRequest,
    FindIdResponse,
    LoginRequest,
    LoginResponse,
    PreviousAccountResponse,
    ResetPasswordRequest,
    RestoredAccountResponse,
    RestoreRequest,
    SendVerificationRequest,
    SignUpRequest,
    TokenRefreshResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService
from app.services.email_verification import EmailVerificationService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def signup(
    request: Request,
    payload: SignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    await auth_service.signup(payload)
    return Response(content={"detail": "회원가입이 성공적으로 완료되었습니다."}, status_code=status.HTTP_201_CREATED)


@auth_router.get("/check-email", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def check_email_available(
    request: Request,
    email: Annotated[str, Query(min_length=3, max_length=80)],
) -> Response:
    """이메일 사용 가능 여부 확인. 가입 폼의 중복 확인 버튼에서 호출."""
    exists = await UserRepository().exists_by_email(email)
    return Response(content={"email": email, "available": not exists}, status_code=status.HTTP_200_OK)


@auth_router.get("/check-nickname", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def check_nickname_available(
    request: Request,
    nickname: Annotated[str, Query(min_length=2, max_length=10)],
) -> Response:
    """닉네임 사용 가능 여부 확인. (ERD: USER.nickname varchar(10) NN unique)"""
    exists = await UserRepository().exists_by_nickname(nickname)
    return Response(content={"nickname": nickname, "available": not exists}, status_code=status.HTTP_200_OK)


@auth_router.post("/find-id", response_model=FindIdResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def find_id(
    request: Request,
    payload: FindIdRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """이름 + 휴대폰 번호로 가입 이메일(마스킹) 조회. 미일치 시 404."""
    result = await auth_service.find_id(payload)
    return Response(content=result.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@auth_router.get("/previous-account", response_model=PreviousAccountResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def previous_account(
    request: Request,
    email: Annotated[str, Query(min_length=3, max_length=80)],
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """재가입 시 복구 가능한 탈퇴 계정 감지. 인증 전이므로 마스킹 이메일·탈퇴일·복구마감만. 없으면 404."""
    result = await auth_service.get_previous_account(email)
    return Response(content=result.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@auth_router.post("/restore", response_model=RestoredAccountResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def restore_account(
    request: Request,
    payload: RestoreRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """탈퇴 계정 복구. 이메일 본인 인증 필수. 복구 후 상세 통계 반환. 미인증 400 / 미존재 404."""
    result = await auth_service.restore_account(str(payload.email))
    return Response(content=result.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@auth_router.post("/destroy", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def destroy_previous_account(
    request: Request,
    payload: DestroyRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """탈퇴 계정 즉시 영구 파기('새로 시작하기'). 이메일 본인 인증 필수. 미인증 400 / 미존재 404 / 정지 403."""
    await auth_service.destroy_previous_account(str(payload.email))
    return Response(content={"detail": "이전 계정이 파기되었습니다."}, status_code=status.HTTP_200_OK)


@auth_router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """비밀번호 재설정(비밀번호 찾기). 이메일 본인 인증 + email/name 일치 필수. 기존과 동일한 비번 거부."""
    await auth_service.reset_password(str(payload.email), payload.name, payload.new_password)
    return Response(content={"detail": "비밀번호가 변경되었습니다."}, status_code=status.HTTP_200_OK)


@auth_router.post("/email/send-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def send_email_verification(
    request: Request,
    payload: SendVerificationRequest,
    service: Annotated[EmailVerificationService, Depends(EmailVerificationService)],
) -> Response:
    """입력 이메일로 본인 인증 링크 메일을 발송한다. (계정 열거 방지: 항상 202)

    name 이 함께 오면(비밀번호 찾기) email+name 일치 계정에만 발송한다 — 불일치여도 응답은 동일한 202.
    """
    await service.send_verification(str(payload.email), payload.name)
    return Response(content={"detail": "인증 메일을 발송했습니다."}, status_code=status.HTTP_202_ACCEPTED)


@auth_router.post("/email/verify", response_model=VerifyEmailResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    service: Annotated[EmailVerificationService, Depends(EmailVerificationService)],
) -> Response:
    """인증 링크의 토큰을 검증하고 이메일을 인증 완료 처리한다. 유효하지 않으면 400."""
    email = await service.verify(payload.token)
    return Response(
        content=VerifyEmailResponse(email=email, verified=True).model_dump(), status_code=status.HTTP_200_OK
    )


@auth_router.get("/email/verification-status", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def email_verification_status(
    request: Request,
    email: Annotated[str, Query(min_length=3, max_length=80)],
    service: Annotated[EmailVerificationService, Depends(EmailVerificationService)],
) -> Response:
    """이메일 인증 완료 여부 조회. 가입폼의 '인증 완료 확인' 버튼에서 호출."""
    verified = await service.is_verified(email)
    return Response(content={"email": email, "verified": verified}, status_code=status.HTTP_200_OK)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    user = await auth_service.authenticate(payload)
    tokens = await auth_service.login(user)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(), status_code=status.HTTP_200_OK
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        samesite="lax",  # api.↔apex 는 same-site 서브도메인 → lax 로 쿠키 정상 전달
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["access_token"].payload["exp"],
    )
    return resp


@auth_router.get("/token/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing.")
    access_token = jwt_service.refresh_jwt(refresh_token)
    return Response(
        content=TokenRefreshResponse(access_token=str(access_token)).model_dump(), status_code=status.HTTP_200_OK
    )
