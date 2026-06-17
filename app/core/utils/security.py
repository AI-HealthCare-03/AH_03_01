import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid

from passlib.context import CryptContext

from app.core import config

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
