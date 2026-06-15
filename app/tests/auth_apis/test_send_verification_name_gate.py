"""인증 메일 발송(POST /api/v1/auth/email/send-verification) name 게이트 테스트.

비밀번호 찾기 흐름에서 name 이 함께 오면 email+name 일치 계정에만 실제 메일이 발송돼야 한다.
- name 일치 → 메일 발송 + 토큰 저장
- name 불일치 / 미존재 계정 → 메일 미발송 (단 응답은 항상 202 — account enumeration 방어)
- name 미전달(회원가입 흐름) → 기존 동작 그대로 무조건 발송

Redis(_client)·실제 메일 발송(send_email)은 mock 으로 격리한다.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.utils.security import hash_password
from app.main import app
from app.models.users import Gender, User

BASE_URL = "http://test"


async def _create_user(
    email: str = "gate_send@example.com",
    name: str = "홍길동",
    *,
    is_deleted: bool = False,
) -> User:
    return await User.create(
        email=email,
        hashed_password=hash_password("OldPass123!"),
        name=name,
        nickname=None,
        phone_number="01000000000",
        birthday=date(1990, 1, 1),
        gender=Gender.MALE,
        is_active=not is_deleted,
        is_deleted=is_deleted,
    )


class TestSendVerificationNameGate(TestCase):
    async def _post(self, body: dict[str, object]) -> tuple[int, AsyncMock]:
        """send_email·Redis 를 mock 한 채 send-verification 호출. (status, send_email mock) 반환."""
        send_email_mock = AsyncMock()
        redis_mock = AsyncMock()
        with (
            patch("app.services.email_verification.send_email", send_email_mock),
            patch("app.services.email_verification._client", return_value=redis_mock),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/email/send-verification", json=body)
        return res.status_code, send_email_mock

    async def test_sends_when_email_and_name_match(self):
        user = await _create_user(email="match@example.com", name="홍길동")
        code, send_email_mock = await self._post({"email": user.email, "name": "홍길동"})
        assert code == status.HTTP_202_ACCEPTED
        send_email_mock.assert_awaited_once()

    async def test_no_mail_when_name_mismatch_but_still_202(self):
        user = await _create_user(email="mismatch@example.com", name="홍길동")
        code, send_email_mock = await self._post({"email": user.email, "name": "김철수"})
        # account enumeration 방어: 응답은 동일한 202
        assert code == status.HTTP_202_ACCEPTED
        # 그러나 실제 메일은 발송되지 않는다 (핵심 버그 회귀 방지)
        send_email_mock.assert_not_awaited()

    async def test_no_mail_when_account_absent_but_still_202(self):
        code, send_email_mock = await self._post({"email": "ghost@example.com", "name": "없음"})
        assert code == status.HTTP_202_ACCEPTED
        send_email_mock.assert_not_awaited()

    async def test_no_mail_for_deleted_account(self):
        user = await _create_user(email="deleted_send@example.com", name="홍길동", is_deleted=True)
        code, send_email_mock = await self._post({"email": user.email, "name": "홍길동"})
        assert code == status.HTTP_202_ACCEPTED
        send_email_mock.assert_not_awaited()

    async def test_signup_flow_without_name_always_sends(self):
        # name 미전달(회원가입 흐름) — 계정 존재 여부와 무관하게 무조건 발송(기존 동작 유지).
        code, send_email_mock = await self._post({"email": "newsignup@example.com"})
        assert code == status.HTTP_202_ACCEPTED
        send_email_mock.assert_awaited_once()
