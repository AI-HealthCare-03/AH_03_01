from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app


class TestLoginAPI(TestCase):
    async def test_login_success(self):
        # 먼저 사용자 등록
        signup_data = {
            "email": "login_test@example.com",
            "password": "Password123!",
            "name": "로그인테스터",
            "nickname": "로그인테스",
            "gender": "FEMALE",
            "birth_date": "1995-05-05",
            "phone_number": "01011112222",
        }
        login_data = {"email": "login_test@example.com", "password": "Password123!"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=signup_data)

            # 로그인 시도
            response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()
        # 쿠키 검증 대신 응답 헤더 확인
        assert any("refresh_token" in header for header in response.headers.get_list("set-cookie"))

    async def test_login_invalid_credentials(self):
        login_data = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/login", json=login_data)

        # AuthService.authenticate 에서 실패 시 HTTP_400_BAD_REQUEST 발생
        assert response.status_code == status.HTTP_400_BAD_REQUEST
