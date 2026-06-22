"""비밀번호 재설정 엔드포인트(POST /api/v1/auth/reset-password) 테스트.

이메일 본인 인증 + email/name 일치 후 새 비밀번호 설정(비밀번호 찾기).
- 해피패스(해시 갱신) / 미인증(400) / 미존재·name 불일치·탈퇴계정(404)
- 새 비밀번호가 기존과 동일하면 "이미 사용 중인 비밀번호입니다"(400)

Redis(consume)·이메일 인증은 patch/autouse 로 격리.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.utils.security import hash_password, verify_password
from app.main import app
from app.models.users import Gender, User
from app.services.email_verification import EmailVerificationService

BASE_URL = "http://test"
OLD_PW = "OldPass123!"
NEW_PW = "NewPass456!"


async def _create_user(
    email: str = "reset@example.com",
    name: str = "홍길동",
    *,
    password: str = OLD_PW,
    is_deleted: bool = False,
) -> User:
    return await User.create(
        email=email,
        hashed_password=hash_password(password),
        name=name,
        nickname=None,
        phone_number="01000000000",
        birthday=date(1990, 1, 1),
        gender=Gender.MALE,
        is_active=not is_deleted,
        is_deleted=is_deleted,
    )


class TestResetPassword(TestCase):
    async def test_reset_success(self):
        user = await _create_user()
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/reset-password",
                    json={"email": user.email, "name": user.name, "new_password": NEW_PW},
                )
        assert res.status_code == status.HTTP_200_OK
        await user.refresh_from_db()
        assert verify_password(NEW_PW, user.hashed_password)  # 새 비번으로 갱신
        assert not verify_password(OLD_PW, user.hashed_password)

    async def test_reset_rejects_same_password(self):
        user = await _create_user(email="same@example.com")
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/reset-password",
                    json={"email": user.email, "name": user.name, "new_password": OLD_PW},
                )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "이미 사용 중인 비밀번호" in res.json()["detail"]
        await user.refresh_from_db()
        assert verify_password(OLD_PW, user.hashed_password)  # 변경 안 됨

    async def test_reset_requires_email_verification(self):
        user = await _create_user(email="unverified@example.com")
        with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=False)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/reset-password",
                    json={"email": user.email, "name": user.name, "new_password": NEW_PW},
                )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        await user.refresh_from_db()
        assert verify_password(OLD_PW, user.hashed_password)

    async def test_reset_not_found_when_name_mismatch(self):
        user = await _create_user(email="mismatch@example.com", name="홍길동")
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post(
                "/api/v1/auth/reset-password",
                json={"email": user.email, "name": "김철수", "new_password": NEW_PW},
            )
        assert res.status_code == status.HTTP_404_NOT_FOUND
        await user.refresh_from_db()
        assert verify_password(OLD_PW, user.hashed_password)

    async def test_reset_not_found_when_no_account(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post(
                "/api/v1/auth/reset-password",
                json={"email": "ghost@example.com", "name": "없음", "new_password": NEW_PW},
            )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_reset_rejects_weak_password(self):
        # 복잡도 정책(대/소/특수/숫자) 미충족 → 422 검증 실패.
        user = await _create_user(email="weak@example.com")
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post(
                "/api/v1/auth/reset-password",
                json={"email": user.email, "name": user.name, "new_password": "12345678"},
            )
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_reset_not_found_for_deleted_account(self):
        user = await _create_user(email="deleted@example.com", is_deleted=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post(
                "/api/v1/auth/reset-password",
                json={"email": user.email, "name": user.name, "new_password": NEW_PW},
            )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_reset_rejects_social_account(self):
        # 소셜(카카오) 전용 계정에 reset_password 로 사용 가능한 비번을 심으면 이메일+비번 로그인 경로가 열림 → 차단.
        user = await User.create(
            email="social_reset@example.com",
            hashed_password=hash_password(OLD_PW),
            name="카카오",
            nickname=None,
            phone_number="01088887777",
            birthday=date(1990, 1, 1),
            gender=Gender.MALE,
            social_provider="kakao",
            social_id="reset-sx1",
        )
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post(
                    "/api/v1/auth/reset-password",
                    json={"email": user.email, "name": user.name, "new_password": NEW_PW},
                )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        await user.refresh_from_db()
        assert verify_password(OLD_PW, user.hashed_password)  # 비밀번호 미변경
