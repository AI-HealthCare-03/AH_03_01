import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid

import redis.asyncio as redis_async
from passlib.context import CryptContext

from app.core import config

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# OAuth state(CSRF 방지 토큰) 유효 시간(초). 발급 후 이 시간 경과 시 verify 가 거부한다.
OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def generate_unusable_password() -> str:
    """비밀번호 로그인이 불가능한 소셜 계정용 해시를 생성한다.

    랜덤 시크릿을 해시하므로 어떤 평문으로도 verify_password 가 통과하지 못한다.
    """
    return hash_password(secrets.token_urlsafe(32))


def _sign_oauth_state(payload_b64: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def generate_oauth_state() -> str:
    """HMAC 서명된 OAuth state(CSRF 토큰)를 생성한다. 형식: base64url(json).<hmac_hex>"""
    payload = {"nonce": uuid.uuid4().hex, "ts": int(time.time())}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{payload_b64}.{_sign_oauth_state(payload_b64)}"


def verify_oauth_state(state: str) -> bool:
    """OAuth state 의 HMAC 서명과 발급 시각(10분 이내)을 검증한다."""
    try:
        payload_b64, signature = state.split(".", 1)
    except ValueError:
        return False

    expected = _sign_oauth_state(payload_b64)
    if not hmac.compare_digest(expected, signature):
        return False

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        ts = int(payload["ts"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False

    return time.time() - ts <= OAUTH_STATE_MAX_AGE_SECONDS


_OAUTH_STATE_KEY = "oauth_state:{nonce}"
_redis: redis_async.Redis | None = None


def _state_client() -> redis_async.Redis:
    global _redis
    if _redis is None:
        _redis = redis_async.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
    return _redis


def _extract_nonce(state: str) -> str | None:
    """서명 검증과 무관하게 state payload 에서 nonce 만 추출한다(단일사용 키 식별용)."""
    try:
        payload_b64 = state.split(".", 1)[0]
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        nonce = payload.get("nonce")
        return str(nonce) if nonce else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


async def register_oauth_state(state: str) -> None:
    """발급한 state 의 nonce 를 Redis 에 단일사용 마커로 저장한다(TTL = state 유효시간).

    Redis 장애 시 조용히 통과(fail-open) — HMAC 서명+발급시각 검증이 1차 방어로 남는다.
    """
    nonce = _extract_nonce(state)
    if nonce is None:
        return
    try:
        await _state_client().setex(_OAUTH_STATE_KEY.format(nonce=nonce), OAUTH_STATE_MAX_AGE_SECONDS, "1")
    except Exception as err:  # noqa: BLE001 — Redis 장애가 로그인 발급 자체를 막지 않도록
        logger.warning("OAuth state 등록 실패(Redis), 단일사용 검증 생략: %s", err)


async def consume_oauth_state(state: str) -> bool:
    """state 를 1회 소비한다. 처음 소비면 True, 이미 쓰였거나 만료면 False(replay 차단).

    Redis 장애 시 True(fail-open) — 단일사용만 건너뛰고 HMAC/TTL 검증은 verify_oauth_state 가 담당.
    """
    nonce = _extract_nonce(state)
    if nonce is None:
        return False
    try:
        deleted = await _state_client().delete(_OAUTH_STATE_KEY.format(nonce=nonce))
        return bool(deleted)
    except Exception as err:  # noqa: BLE001 — Redis 장애 시 단일사용 검증만 포기, 로그인은 막지 않음
        logger.warning("OAuth state 소비 실패(Redis), replay 검증 생략: %s", err)
        return True
