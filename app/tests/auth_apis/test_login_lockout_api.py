"""로그인 5회 실패 잠금 + 이메일 인증 해제 테스트.

- 연속 5회 실패 시 423 잠금, 이후 올바른 비번도 423.
- 로그인 성공 시 누적 실패 카운트 초기화.
- POST /auth/unlock: 이메일 본인 인증 + email/name 일치로 잠금 해제(카운트 0).
  미인증(400) / name 불일치(404).

이메일 인증(is_verified)은 conftest autouse 로 True 목킹됨.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.utils.security import hash_password
from app.main import app
from app.models.users import Gender, User
from app.services.email_verification import EmailVerificationService

BASE_URL = "http://test"
PW = "LockPass123!"


async def _create_user(
    email: str = "lock@example.com",
    name: str = "홍길동",
    *,
    login_fail_count: int = 0,
) -> User:
    return await User.create(
        email=email,
        hashed_password=hash_password(PW),
        name=name,
        nickname=None,
        phone_number="01000000000",
        birthday=date(1990, 1, 1),
        gender=Gender.MALE,
        is_active=True,
        login_fail_count=login_fail_count,
    )


class TestLoginLockout(TestCase):
    async def test_failure_increments_count(self):
        # 임계 미만 실패는 일반 400 + 카운트 증가 (요청 1회 — IP 레이트리밋 영향 최소화).
        user = await _create_user(email="incr@example.com", login_fail_count=0)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "Wrong999!"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        await user.refresh_from_db()
        assert user.login_fail_count == 1

    async def test_lock_at_threshold(self):
        # 이미 4회 실패한 계정의 5회째 실패 → 잠금(423), 이후 올바른 비번도 423.
        user = await _create_user(email="threshold@example.com", login_fail_count=4)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "Wrong999!"})
            assert res.status_code == status.HTTP_423_LOCKED
            locked = await client.post("/api/v1/auth/login", json={"email": user.email, "password": PW})
            assert locked.status_code == status.HTTP_423_LOCKED
        await user.refresh_from_db()
        assert user.login_fail_count >= 5

    async def test_success_resets_fail_count(self):
        user = await _create_user(email="resetcount@example.com", login_fail_count=3)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post("/api/v1/auth/login", json={"email": user.email, "password": PW})
        assert res.status_code == status.HTTP_200_OK
        await user.refresh_from_db()
        assert user.login_fail_count == 0

    async def test_unlock_resets_and_allows_login(self):
        user = await _create_user(email="unlock@example.com", login_fail_count=5)
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/unlock", json={"email": user.email, "name": user.name}
                )
                assert res.status_code == status.HTTP_200_OK
                await user.refresh_from_db()
                assert user.login_fail_count == 0
                # 해제 후 정상 로그인
                login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": PW})
                assert login.status_code == status.HTTP_200_OK

    async def test_unlock_requires_email_verification(self):
        user = await _create_user(email="unlock_noverify@example.com", login_fail_count=5)
        with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=False)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/unlock", json={"email": user.email, "name": user.name}
                )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        await user.refresh_from_db()
        assert user.login_fail_count == 5  # 변경 안 됨

    async def test_unlock_not_found_when_name_mismatch(self):
        user = await _create_user(email="unlock_mismatch@example.com", name="홍길동", login_fail_count=5)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post(
                "/api/v1/auth/unlock", json={"email": user.email, "name": "김철수"}
            )
        assert res.status_code == status.HTTP_404_NOT_FOUND
        await user.refresh_from_db()
        assert user.login_fail_count == 5
