import logging

import httpx
from fastapi import HTTPException
from starlette import status

from app.core import config

logger = logging.getLogger(__name__)

# 카카오 API 호출 타임아웃(초).
KAKAO_HTTP_TIMEOUT = 5.0


class KakaoProfile:
    """카카오 user info 에서 추출한 최소 프로필. social_id 는 필수, 나머지는 동의 항목이라 없을 수 있다."""

    def __init__(self, social_id: str, email: str | None, nickname: str | None) -> None:
        self.social_id = social_id
        self.email = email
        self.nickname = nickname


class KakaoOAuthService:
    """카카오 OAuth2 토큰 교환 + 사용자 정보 조회. HTTP 경계만 담당(비즈니스 로직은 AuthService)."""

    def _require_config(self) -> None:
        if not (config.KAKAO_REST_API_KEY and config.KAKAO_REDIRECT_URI):
            # 키 미설정은 서버 구성 오류 — 클라이언트 잘못이 아니므로 500.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="카카오 로그인이 구성되지 않았습니다.",
            )

    async def exchange_code(self, code: str) -> str:
        """authorization code 를 카카오 access token 으로 교환한다."""
        self._require_config()
        data = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_REST_API_KEY,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "code": code,
        }
        if config.KAKAO_CLIENT_SECRET:
            data["client_secret"] = config.KAKAO_CLIENT_SECRET

        try:
            async with httpx.AsyncClient(timeout=KAKAO_HTTP_TIMEOUT) as client:
                resp = await client.post(config.KAKAO_TOKEN_URL, data=data)
        except (httpx.TimeoutException, httpx.ConnectError) as err:
            logger.warning("카카오 토큰 교환 통신 실패: %s", err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="카카오 인증 서버에 연결할 수 없습니다."
            ) from err

        if resp.status_code >= 500:
            logger.warning("카카오 토큰 교환 5xx: %s", resp.status_code)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="카카오 인증 서버 오류입니다.")
        if resp.status_code >= 400:
            logger.info("카카오 토큰 교환 거부: %s", resp.status_code)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 인증에 실패했습니다.")

        access_token = resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 인증에 실패했습니다.")
        return str(access_token)

    async def fetch_profile(self, kakao_access_token: str) -> KakaoProfile:
        """카카오 access token 으로 사용자 프로필(id/email/nickname)을 조회한다."""
        self._require_config()
        try:
            async with httpx.AsyncClient(timeout=KAKAO_HTTP_TIMEOUT) as client:
                resp = await client.get(
                    config.KAKAO_USER_INFO_URL,
                    headers={"Authorization": f"Bearer {kakao_access_token}"},
                )
        except (httpx.TimeoutException, httpx.ConnectError) as err:
            logger.warning("카카오 사용자정보 통신 실패: %s", err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="카카오 인증 서버에 연결할 수 없습니다."
            ) from err

        if resp.status_code >= 500:
            logger.warning("카카오 사용자정보 5xx: %s", resp.status_code)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="카카오 인증 서버 오류입니다.")
        if resp.status_code >= 400:
            logger.info("카카오 사용자정보 거부: %s", resp.status_code)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 인증에 실패했습니다.")

        body = resp.json()
        social_id_raw = body.get("id")
        if social_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 사용자 정보를 가져오지 못했습니다."
            )

        account = body.get("kakao_account") or {}
        profile = account.get("profile") or {}
        properties = body.get("properties") or {}
        email = account.get("email")
        nickname = profile.get("nickname") or properties.get("nickname")
        return KakaoProfile(social_id=str(social_id_raw), email=email, nickname=nickname)
