"""회원가입 이메일 인증 게이트 / 인증 레이트리밋 전용 테스트.

conftest 의 autouse 우회(bypass_email_verification, disable_rate_limiter)를
이 테스트들에서는 명시적으로 덮어써 실제 동작을 검증한다.
"""

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.limiter import limiter
from app.main import app
from app.services.email_verification import EmailVerificationService

BASE_URL = "http://test"


def _signup_payload(**override: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "gate_test@example.com",
        "password": "Password123!",
        "name": "게이트",
        "nickname": "게이트테스트",
        "gender": "MALE",
        "birth_date": "1990-01-01",
        "phone_number": "01099990000",
    }
    payload.update(override)
    return payload


class TestSignupEmailVerificationGate(TestCase):
    async def test_signup_blocked_when_email_not_verified(self):
        # autouse 우회를 덮어써 미인증 상태로 만든다.
        with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=False)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/signup", json=_signup_payload())
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "본인 인증" in res.json()["detail"]

    async def test_signup_succeeds_when_email_verified(self):
        with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=True)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/signup",
                    json=_signup_payload(
                        email="gate_ok@example.com", nickname="게이트통과", phone_number="01099990001"
                    ),
                )
        assert res.status_code == status.HTTP_201_CREATED


class TestAuthRateLimit(TestCase):
    async def test_login_rate_limited_after_threshold(self):
        # autouse 로 꺼둔 레이트리밋을 이 테스트에서만 켠다 (login 5/min).
        original = limiter.enabled
        limiter.enabled = True
        try:
            codes = []
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                for _ in range(8):
                    res = await client.post(
                        "/api/v1/auth/login",
                        json={"email": "nobody_rl@example.com", "password": "WrongPass123!"},
                    )
                    codes.append(res.status_code)
        finally:
            limiter.enabled = original
        # 5/min 초과 → 임계 초과분은 429.
        assert status.HTTP_429_TOO_MANY_REQUESTS in codes
        assert codes[-1] == status.HTTP_429_TOO_MANY_REQUESTS
