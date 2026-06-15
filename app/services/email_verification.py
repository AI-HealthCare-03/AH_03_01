import secrets

import redis.asyncio as redis_async
from fastapi.exceptions import HTTPException
from starlette import status

from app.core import config
from app.core.utils.email import send_email

# 인증 토큰은 발급 후 10분, 인증 완료 플래그는 가입까지 15분 유효.
_TOKEN_TTL_SEC = 10 * 60
_VERIFIED_TTL_SEC = 15 * 60
_TOKEN_KEY = "email_verify:token:{token}"
_VERIFIED_KEY = "email_verify:verified:{email}"

_redis: redis_async.Redis | None = None


def _client() -> redis_async.Redis:
    global _redis
    if _redis is None:
        _redis = redis_async.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
    return _redis


class EmailVerificationService:
    async def send_verification(self, email: str, name: str | None = None) -> None:
        """인증 토큰을 발급해 Redis 에 저장하고 인증 링크를 메일로 발송한다.

        name 이 주어지면(비밀번호 찾기 흐름) email+name 이 일치하는 활성 계정이 있을 때만 실제로
        메일을 발송한다. 불일치/미존재여도 예외 없이 조용히 반환한다 — 라우터는 항상 202 를 반환하므로
        이메일·이름 존재 여부가 응답으로 노출되지 않는다(account enumeration 방어).
        name 이 없으면(회원가입 흐름) 기존 동작 그대로 무조건 발송한다.
        """
        if name is not None:
            # 지연 import — repositories ↔ services 순환 의존 방지
            from app.repositories.user_repository import UserRepository  # noqa: PLC0415

            user = await UserRepository().get_active_user_by_email_and_name(email, name)
            if user is None:
                return  # 일치 계정 없음 — 조용히 종료(응답은 라우터에서 동일하게 202)

        token = secrets.token_urlsafe(32)
        await _client().set(_TOKEN_KEY.format(token=token), email, ex=_TOKEN_TTL_SEC)

        link = f"{config.FRONTEND_BASE_URL}/verify-email?token={token}"
        body = f"아래 링크를 클릭하면 이메일 본인 인증이 완료됩니다.\n\n{link}\n\n링크는 10분간 유효합니다."
        await send_email(email, "[케어로그] 이메일 본인 인증", body)

    async def verify(self, token: str) -> str:
        """토큰을 검증하고 해당 이메일을 인증 완료 처리한다. 토큰은 1회용."""
        client = _client()
        token_key = _TOKEN_KEY.format(token=token)
        email = await client.get(token_key)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않거나 만료된 인증 링크입니다."
            )

        await client.set(_VERIFIED_KEY.format(email=email), "1", ex=_VERIFIED_TTL_SEC)
        await client.delete(token_key)
        return email

    async def is_verified(self, email: str) -> bool:
        """이메일이 인증 완료 상태인지 여부. (가입 게이트 / 완료 확인 버튼에서 사용)"""
        return bool(await _client().exists(_VERIFIED_KEY.format(email=email)))

    async def consume(self, email: str) -> None:
        """가입 완료 후 인증 완료 플래그를 제거한다. (1회용 — 재사용 방지)"""
        await _client().delete(_VERIFIED_KEY.format(email=email))
