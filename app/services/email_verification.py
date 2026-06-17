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
# purpose 가 지정된 흐름(예: 로그인 상태 비밀번호 변경)은 별도 네임스페이스로 격리해, 다른
# 흐름(가입/비번찾기 등)에서 남은 verified 플래그로 게이트가 통과되는 교차흐름 재사용을 막는다.
_VERIFIED_KEY_NS = "email_verify:verified:{purpose}:{email}"
# 토큰별 purpose 사이드카 — verify(메일 링크) 시점에 어느 네임스페이스에 플래그를 세울지 결정.
_PURPOSE_KEY = "email_verify:purpose:{token}"

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


def _verified_key(email: str, purpose: str | None) -> str:
    """purpose 없으면 기존 공유 키, 있으면 purpose 격리 키. (기존 흐름 무회귀)"""
    if purpose:
        return _VERIFIED_KEY_NS.format(purpose=purpose, email=email)
    return _VERIFIED_KEY.format(email=email)


class EmailVerificationService:
    async def send_verification(self, email: str, name: str | None = None, purpose: str | None = None) -> None:
        """인증 토큰을 발급해 Redis 에 저장하고 인증 링크를 메일로 발송한다.

        name 이 주어지면(비밀번호 찾기 흐름) email+name 이 일치하는 활성 계정이 있을 때만 실제로
        메일을 발송한다. 불일치/미존재여도 예외 없이 조용히 반환한다 — 라우터는 항상 202 를 반환하므로
        이메일·이름 존재 여부가 응답으로 노출되지 않는다(account enumeration 방어).
        name 이 없으면(회원가입 흐름) 기존 동작 그대로 무조건 발송한다.

        purpose 가 주어지면 인증 완료 플래그를 그 네임스페이스에 격리한다(verify 시점에 적용).
        """
        if name is not None:
            # 지연 import — repositories ↔ services 순환 의존 방지
            from app.repositories.user_repository import UserRepository  # noqa: PLC0415

            user = await UserRepository().get_active_user_by_email_and_name(email, name)
            if user is None:
                return  # 일치 계정 없음 — 조용히 종료(응답은 라우터에서 동일하게 202)

        token = secrets.token_urlsafe(32)
        await _client().set(_TOKEN_KEY.format(token=token), email, ex=_TOKEN_TTL_SEC)
        if purpose:
            await _client().set(_PURPOSE_KEY.format(token=token), purpose, ex=_TOKEN_TTL_SEC)

        link = f"{config.FRONTEND_BASE_URL}/verify-email?token={token}"
        body = f"아래 링크를 클릭하면 이메일 본인 인증이 완료됩니다.\n\n{link}\n\n링크는 10분간 유효합니다."
        await send_email(email, "[케어로그] 이메일 본인 인증", body)

    async def verify(self, token: str) -> str:
        """토큰을 검증하고 해당 이메일을 인증 완료 처리한다. 토큰은 1회용."""
        client = _client()
        token_key = _TOKEN_KEY.format(token=token)
        purpose_key = _PURPOSE_KEY.format(token=token)
        email = await client.get(token_key)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않거나 만료된 인증 링크입니다."
            )

        purpose = await client.get(purpose_key)  # purpose 미지정 흐름/구토큰은 None → 기존 공유 키
        await client.set(_verified_key(email, purpose), "1", ex=_VERIFIED_TTL_SEC)
        await client.delete(token_key)
        await client.delete(purpose_key)
        return email

    async def is_verified(self, email: str, purpose: str | None = None) -> bool:
        """이메일이 (해당 purpose 로) 인증 완료 상태인지 여부. (게이트 / 완료 확인 버튼에서 사용)"""
        return bool(await _client().exists(_verified_key(email, purpose)))

    async def consume(self, email: str, purpose: str | None = None) -> None:
        """인증 완료 플래그를 제거한다. (1회용 — 재사용 방지)"""
        await _client().delete(_verified_key(email, purpose))
