from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.core.jwt.tokens import AccessToken, RefreshToken
from app.core.limiter import limiter
from app.core.utils.security import generate_oauth_state, register_oauth_state
from app.dtos.auth import (
    DestroyRequest,
    FindIdRequest,
    FindIdResponse,
    KakaoAuthorizeUrlResponse,
    KakaoCallbackRequest,
    KakaoRestoreTicketRequest,
    KakaoSignupRequest,
    LoginRequest,
    LoginResponse,
    PreviousAccountResponse,
    ResetPasswordRequest,
    RestoredAccountResponse,
    RestoreRequest,
    SendVerificationRequest,
    SignUpRequest,
    TokenRefreshResponse,
    UnlockAccountRequest,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService
from app.services.email_verification import EmailVerificationService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(resp: Response, tokens: dict[str, AccessToken | RefreshToken]) -> None:
    """로그인/가입 응답에 refresh_token httponly 쿠키를 심는다. (/login 과 동일 정책)"""
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        samesite="lax",  # api.↔apex 는 same-site 서브도메인 → lax 로 쿠키 정상 전달
        domain=config.COOKIE_DOMAIN or None,
        # 쿠키 만료는 refresh_token TTL 기준 — access TTL(15분)로 잡으면 refresh 가 유효해도
        # 브라우저가 쿠키를 먼저 삭제해 재로그인이 강제된다.
        expires=tokens["refresh_token"].payload["exp"],
    )


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


@auth_router.post("/unlock", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def unlock_account(
    request: Request,
    payload: UnlockAccountRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """로그인 5회 실패로 잠긴 계정 해제. 이메일 본인 인증 + email/name 일치 필수."""
    await auth_service.unlock_account(str(payload.email), payload.name)
    return Response(content={"detail": "계정 잠금이 해제되었습니다."}, status_code=status.HTTP_200_OK)


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
    await service.send_verification(str(payload.email), payload.name, payload.purpose)
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
    purpose: Annotated[str | None, Query(max_length=40)] = None,
) -> Response:
    """이메일 인증 완료 여부 조회. 가입폼/비번변경의 '인증 완료 확인' 버튼에서 호출."""
    verified = await service.is_verified(email, purpose)
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
        # 쿠키 만료는 refresh_token TTL 기준 — access TTL(15분)로 잡으면 refresh 가 유효해도
        # 브라우저가 쿠키를 먼저 삭제해 재로그인이 강제된다.
        expires=tokens["refresh_token"].payload["exp"],
    )
    return resp


@auth_router.get("/kakao/authorize-url", response_model=KakaoAuthorizeUrlResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def kakao_authorize_url(request: Request) -> Response:
    """카카오 인가 페이지로 보낼 authorize URL + CSRF state 를 발급한다. 프론트가 이 URL 로 리다이렉트."""
    state = generate_oauth_state()
    await register_oauth_state(state)  # 단일사용 마커 등록 — 콜백에서 1회만 소비 가능(replay 차단)
    query = urlencode(
        {
            "client_id": config.KAKAO_REST_API_KEY,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "response_type": "code",
            # 닉네임만 요청. 이메일(account_email)은 비즈앱 권한이 필요해 기본 "권한 없음" 이고,
            # 권한 없는 scope 를 요청하면 인가 단계에서 에러(KOE006)가 난다. 이메일은 가입 폼에서 직접 수집.
            "scope": "profile_nickname",
            # 매 로그인마다 카카오 로그인/동의 화면을 강제로 다시 띄운다(SSO 세션 무시).
            # 이전 인증 캐시로 silent 하게 code 만 받아오는 것을 막아 본인 재확인을 보장한다.
            "prompt": "login",
            "state": state,
        }
    )
    authorize_url = f"{config.KAKAO_AUTHORIZE_URL}?{query}"
    return Response(
        content=KakaoAuthorizeUrlResponse(authorize_url=authorize_url, state=state).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/kakao/callback", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def kakao_callback(
    request: Request,
    payload: KakaoCallbackRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """카카오 콜백. 기존 계정이면 로그인(refresh 쿠키 설정), 신규면 가입 티켓을 반환한다."""
    result, tokens = await auth_service.kakao_callback(payload.code, payload.state)
    resp = Response(content=result.model_dump(mode="json"), status_code=status.HTTP_200_OK)
    if tokens is not None:
        _set_refresh_cookie(resp, tokens)
    return resp


@auth_router.post("/kakao/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def kakao_signup(
    request: Request,
    payload: KakaoSignupRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """카카오 가입 티켓 + 추가 입력으로 신규 소셜 계정을 생성하고 로그인 토큰을 발급한다."""
    tokens = await auth_service.kakao_signup(payload)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )
    _set_refresh_cookie(resp, tokens)
    return resp


@auth_router.post("/kakao/restore", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def kakao_restore(
    request: Request,
    payload: KakaoRestoreTicketRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """카카오 복구 티켓으로 탈퇴 계정을 복구하고 바로 로그인(refresh 쿠키 설정)한다."""
    tokens = await auth_service.kakao_restore(payload.restore_ticket)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(),
        status_code=status.HTTP_200_OK,
    )
    _set_refresh_cookie(resp, tokens)
    return resp


@auth_router.post("/kakao/destroy", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def kakao_destroy(
    request: Request,
    payload: KakaoRestoreTicketRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """카카오 복구 티켓으로 탈퇴 계정을 영구 파기('새로 시작하기')한다."""
    await auth_service.kakao_destroy(payload.restore_ticket)
    return Response(content={"detail": "이전 계정이 파기되었습니다."}, status_code=status.HTTP_200_OK)


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
