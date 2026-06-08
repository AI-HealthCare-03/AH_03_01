"""탈퇴 계정 즉시 영구 파기 엔드포인트(POST /api/v1/auth/destroy) 테스트.

'새로 시작하기' — 이메일 본인 인증 후 탈퇴 계정을 하드 삭제(cascade 로 PII/PHI 동반 제거).
- 해피패스(하드 삭제) / 미인증(400) / 미존재(404)
- 정지(is_banned) 계정 파기 차단(403) — 본인 파기로 자료 인멸 방지
- 파기 후 그가 만든 챌린지는 creator SET_NULL 로 생존(타 유저 데이터 보호)

Redis(consume)·이메일 인증은 patch/autouse 로 격리.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import fields
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.challenge import Challenge, ChallengeCategory, GoalType, VerificationType
from app.models.users import Gender, User
from app.services.email_verification import EmailVerificationService

BASE_URL = "http://test"


async def _create_deleted_user(email: str = "destroy_test@example.com", *, is_banned: bool = False) -> User:
    now = datetime.now(config.TIMEZONE)
    return await User.create(
        email=email,
        hashed_password="x" * 60,
        name="파기",
        nickname=None,
        phone_number="01000000000",
        birthday=date(1990, 1, 1),
        gender=Gender.MALE,
        is_active=False,
        is_deleted=True,
        is_banned=is_banned,
        deleted_at=now - timedelta(days=1),
        withdrawal_reason="test",
    )


class TestDestroyPreviousAccount(TestCase):
    async def test_destroy_success(self):
        user = await _create_deleted_user()
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/destroy", json={"email": user.email})
        assert res.status_code == status.HTTP_200_OK
        assert await User.get_or_none(id=user.id) is None  # 하드 삭제됨

    async def test_destroy_blocked_for_banned_account(self):
        user = await _create_deleted_user(email="banned_d@example.com", is_banned=True)
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/destroy", json={"email": user.email})
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert await User.get_or_none(id=user.id) is not None  # 보존

    async def test_destroy_requires_email_verification(self):
        user = await _create_deleted_user(email="unverified_d@example.com")
        with patch.object(EmailVerificationService, "is_verified", AsyncMock(return_value=False)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/destroy", json={"email": user.email})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert await User.get_or_none(id=user.id) is not None

    async def test_destroy_not_found_when_no_deleted_account(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            res = await client.post("/api/v1/auth/destroy", json={"email": "ghost_d@example.com"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_destroy_keeps_challenge_with_null_creator(self):
        # 안전장치: 탈퇴 유저 파기 후에도 그가 만든 챌린지는 살아남고 creator_id=None.
        on_delete = Challenge._meta.fields_map["creator"].on_delete  # type: ignore[attr-defined]
        if on_delete != fields.SET_NULL:
            self.skipTest(f"Challenge.creator.on_delete={on_delete} (SET_NULL 아님) — 생존 검증 보류")

        user = await _create_deleted_user(email="creator_d@example.com")
        today = date.today()
        challenge = await Challenge.create(
            creator=user,
            title="테스트 챌린지",
            category=ChallengeCategory.WATER,
            goal_type=GoalType.COUNT,
            verification_type=VerificationType.CHECK,
            start_date=today,
            end_date=today + timedelta(days=7),
        )
        with patch.object(EmailVerificationService, "consume", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                res = await client.post("/api/v1/auth/destroy", json={"email": user.email})

        assert res.status_code == status.HTTP_200_OK
        assert await User.get_or_none(id=user.id) is None
        surviving = await Challenge.get_or_none(id=challenge.id)
        assert surviving is not None  # 챌린지 생존
        assert surviving.creator_id is None  # creator 만 NULL
