"""탈퇴 계정 복구 엔드포인트(POST /api/v1/auth/restore) 테스트.

해피패스 / 미인증(400) / 미존재·보관기간 만료(404) 기본 동작과,
보안 리뷰(7377c78 후속, 6e27566) 회귀를 함께 검증한다:
- [H-1] 정지(is_banned) 계정 복구 차단(403)
- [M-3] 복구 후 부가 통계 조회 실패 시 폴백(복구는 200 유지)

Redis(consume) / 펫·포인트 의존을 피하기 위해 consume·_account_stats 는 패치한다.
is_verified 는 conftest 의 autouse 우회로 기본 True 이며, 미인증 케이스에서만 덮어쓴다.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.users import Gender, User
from app.services.auth import ACCOUNT_RETENTION_DAYS, AuthService
from app.services.email_verification import EmailVerificationService

BASE_URL = "http://test"
STATS = {"challenge_count": 2, "points": 100, "pet_name": "코코"}


async def _create_deleted_user(
    email: str = "restore_test@example.com",
    *,
    deleted_days_ago: int = 1,
    is_banned: bool = False,
) -> User:
    """복구 대상이 되는 탈퇴(soft delete) 유저를 직접 생성한다."""
    now = datetime.now(config.TIMEZONE)
    return await User.create(
        email=email,
        hashed_password="x" * 60,
        name="복구",
        nickname=None,  # unique=True null=True — None 다건 허용
        phone_number="01000000000",
        birthday=date(1990, 1, 1),
        gender=Gender.MALE,
        is_active=False,
        is_deleted=True,
        is_banned=is_banned,
        deleted_at=now - timedelta(days=deleted_days_ago),
        withdrawal_reason="test",
    )


class TestRestoreAccount(TestCase):
    async def test_restore_success(self):
        user = await _create_deleted_user()
        with (
            patch.object(EmailVerificationService, "consume", AsyncMock()),
            patch.object(AuthService, "_account_stats", AsyncMock(return_value=STATS)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/restore", json={"email": user.email})

        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["email"] == user.email
        assert body["challenge_count"] == 2
        assert body["points"] == 100
        assert body["pet_name"] == "코코"

        await user.refresh_from_db()
        assert user.is_deleted is False
        assert user.is_active is True
        assert user.deleted_at is None
        assert user.withdrawal_reason is None

    async def test_restore_blocked_for_banned_account(self):
        # [H-1] 정지 계정은 복구 거부(403) — is_active 부활로 ban 우회 방지.
        user = await _create_deleted_user(email="banned@example.com", is_banned=True)
        with (
            patch.object(EmailVerificationService, "consume", AsyncMock()),
            patch.object(AuthService, "_account_stats", AsyncMock(return_value=STATS)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/restore", json={"email": user.email})

        assert res.status_code == status.HTTP_403_FORBIDDEN
        await user.refresh_from_db()
        assert user.is_deleted is True  # 여전히 탈퇴 상태로 유지
        assert user.is_active is False

    async def test_restore_requires_email_verification(self):
        # 미인증 → 400 (autouse 우회를 덮어써 미인증 상태로).
        user = await _create_deleted_user(email="unverified@example.com")
        with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=False)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/restore", json={"email": user.email})

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        await user.refresh_from_db()
        assert user.is_deleted is True

    async def test_restore_not_found_when_no_deleted_account(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post("/api/v1/auth/restore", json={"email": "ghost@example.com"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_restore_not_found_when_retention_expired(self):
        user = await _create_deleted_user(email="expired@example.com", deleted_days_ago=ACCOUNT_RETENTION_DAYS + 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post("/api/v1/auth/restore", json={"email": user.email})

        assert res.status_code == status.HTTP_404_NOT_FOUND
        await user.refresh_from_db()
        assert user.is_deleted is True  # 보관기간 만료 — 복구되지 않음

    async def test_restore_succeeds_when_stats_fail(self):
        # [M-3] 부가 통계 조회 실패해도 복구는 200, 통계는 기본값으로 폴백.
        user = await _create_deleted_user(email="statsfail@example.com")
        with (
            patch.object(EmailVerificationService, "consume", AsyncMock()),
            patch.object(AuthService, "_account_stats", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/restore", json={"email": user.email})

        assert res.status_code == status.HTTP_200_OK
        body = res.json()
        assert body["challenge_count"] == 0
        assert body["points"] == 0
        assert body["pet_name"] is None
        await user.refresh_from_db()
        assert user.is_deleted is False
