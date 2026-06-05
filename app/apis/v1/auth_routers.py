from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.dtos.auth import (
    FindIdRequest,
    FindIdResponse,
    LoginRequest,
    LoginResponse,
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
async def signup(
    request: SignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    await auth_service.signup(request)
    return Response(content={"detail": "회원가입이 성공적으로 완료되었습니다."}, status_code=status.HTTP_201_CREATED)


@auth_router.get("/check-email", status_code=status.HTTP_200_OK)
async def check_email_available(
    email: Annotated[str, Query(min_length=3, max_length=80)],
) -> Response:
    """이메일 사용 가능 여부 확인. 가입 폼의 중복 확인 버튼에서 호출."""
    exists = await UserRepository().exists_by_email(email)
    return Response(content={"email": email, "available": not exists}, status_code=status.HTTP_200_OK)


@auth_router.get("/check-nickname", status_code=status.HTTP_200_OK)
async def check_nickname_available(
    nickname: Annotated[str, Query(min_length=2, max_length=10)],
) -> Response:
    """닉네임 사용 가능 여부 확인. (ERD: USER.nickname varchar(10) NN unique)"""
    exists = await UserRepository().exists_by_nickname(nickname)
    return Response(content={"nickname": nickname, "available": not exists}, status_code=status.HTTP_200_OK)


@auth_router.post("/find-id", response_model=FindIdResponse, status_code=status.HTTP_200_OK)
async def find_id(
    request: FindIdRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """이름 + 휴대폰 번호로 가입 이메일(마스킹) 조회. 미일치 시 404."""
    result = await auth_service.find_id(request)
    return Response(content=result.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@auth_router.post("/email/send-verification", status_code=status.HTTP_202_ACCEPTED)
async def send_email_verification(
    request: SendVerificationRequest,
    service: Annotated[EmailVerificationService, Depends(EmailVerificationService)],
) -> Response:
    """입력 이메일로 본인 인증 링크 메일을 발송한다. (계정 열거 방지: 항상 202)"""
    await service.send_verification(str(request.email))
    return Response(content={"detail": "인증 메일을 발송했습니다."}, status_code=status.HTTP_202_ACCEPTED)


@auth_router.post("/email/verify", response_model=VerifyEmailResponse, status_code=status.HTTP_200_OK)
async def verify_email(
    request: VerifyEmailRequest,
    service: Annotated[EmailVerificationService, Depends(EmailVerificationService)],
) -> Response:
    """인증 링크의 토큰을 검증하고 이메일을 인증 완료 처리한다. 유효하지 않으면 400."""
    email = await service.verify(request.token)
    return Response(
        content=VerifyEmailResponse(email=email, verified=True).model_dump(), status_code=status.HTTP_200_OK
    )


@auth_router.get("/email/verification-status", status_code=status.HTTP_200_OK)
async def email_verification_status(
    email: Annotated[str, Query(min_length=3, max_length=80)],
    service: Annotated[EmailVerificationService, Depends(EmailVerificationService)],
) -> Response:
    """이메일 인증 완료 여부 조회. 가입폼의 '인증 완료 확인' 버튼에서 호출."""
    verified = await service.is_verified(email)
    return Response(content={"email": email, "verified": verified}, status_code=status.HTTP_200_OK)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    user = await auth_service.authenticate(request)
    tokens = await auth_service.login(user)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(), status_code=status.HTTP_200_OK
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
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
