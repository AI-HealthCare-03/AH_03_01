from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app


class TestSignupAPI(TestCase):
    async def test_signup_success(self):
        signup_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "name": "테스터",
            "nickname": "테스터1",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone_number": "01012345678",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {"detail": "회원가입이 성공적으로 완료되었습니다."}

    async def test_signup_invalid_email(self):
        signup_data = {
            "email": "invalid-email",
            "password": "password123!",
            "name": "테스터",
            "nickname": "테스터2",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone_number": "01012345678",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
