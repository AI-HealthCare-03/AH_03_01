from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.services.email_verification import EmailVerificationService

BASE_URL = "http://test"
OLD_PW = "Password123!"
NEW_PW = "Password456!"


async def _signup_and_login(client: AsyncClient, email: str, phone: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": OLD_PW,
            "name": "비번변경테스터",
            "nickname": f"u{phone[-5:]}",
            "gender": "FEMALE",
            "birth_date": "1992-02-02",
            "phone_number": phone,
        },
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": OLD_PW})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class TestChangePasswordApi(TestCase):
    async def test_change_password_success_when_verified(self):
        # bypass_email_verification 픽스처가 is_verified=True 로 통과. consume 은 Redis 회피용 패치.
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            headers = await _signup_and_login(client, "pw_ok@example.com", "01055550001")
            with patch.object(EmailVerificationService, "consume", AsyncMock()):
                res = await client.post(
                    "/api/v1/users/me/password",
                    json={"current_password": OLD_PW, "new_password": NEW_PW},
                    headers=headers,
                )
            assert res.status_code == status.HTTP_204_NO_CONTENT
            # 새 비밀번호로 로그인 가능, 기존 비밀번호로는 불가
            ok = await client.post("/api/v1/auth/login", json={"email": "pw_ok@example.com", "password": NEW_PW})
            assert ok.status_code == status.HTTP_200_OK

    async def test_change_password_requires_email_verification(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            headers = await _signup_and_login(client, "pw_unverified@example.com", "01055550002")
            with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=False)):
                res = await client.post(
                    "/api/v1/users/me/password",
                    json={"current_password": OLD_PW, "new_password": NEW_PW},
                    headers=headers,
                )
            assert res.status_code == status.HTTP_400_BAD_REQUEST
            assert "이메일 본인 인증" in res.json()["detail"]
            # 비밀번호 미변경 — 기존 비밀번호로 여전히 로그인 가능
            still = await client.post(
                "/api/v1/auth/login", json={"email": "pw_unverified@example.com", "password": OLD_PW}
            )
            assert still.status_code == status.HTTP_200_OK

    async def test_change_password_rejects_wrong_current(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            headers = await _signup_and_login(client, "pw_wrong@example.com", "01055550003")
            res = await client.post(
                "/api/v1/users/me/password",
                json={"current_password": "WrongPassword1!", "new_password": NEW_PW},
                headers=headers,
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST
