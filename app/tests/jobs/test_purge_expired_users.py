"""30일 경과 탈퇴 계정 영구 파기 잡(app.jobs.purge_expired_users) 통합 테스트.

검증:
- 보관기간(ACCOUNT_RETENTION_DAYS) 초과 탈퇴 유저 → 하드 삭제됨
- 보관기간 미만 탈퇴 유저 → 보존
- 정상(is_deleted=False) 유저 → 보존
- --dry-run → 아무도 삭제되지 않음
- (안전장치 핵심) 탈퇴 유저가 만든 챌린지는 user 삭제 후에도 살아남고 creator_id=None

conftest 가 모델 기반으로 test 스키마를 생성하므로 Challenge.creator 의 on_delete
변경(SET_NULL)도 자동 반영된다. 변경 전(CASCADE)에는 챌린지 생존 테스트가 자동 skip 된다.
"""

from datetime import date, datetime, timedelta

from tortoise import fields
from tortoise.contrib.test import TestCase

from app.core import config
from app.jobs.purge_expired_users import parse_args, purge_expired_users
from app.models.challenge import (
    Challenge,
    ChallengeCategory,
    GoalType,
    VerificationType,
)
from app.models.users import Gender, User
from app.services.auth import ACCOUNT_RETENTION_DAYS


async def _create_user(
    email: str,
    *,
    is_deleted: bool = True,
    deleted_days_ago: int | None = None,
) -> User:
    """탈퇴/정상 유저를 직접 생성한다."""
    now = datetime.now(config.TIMEZONE)
    deleted_at = now - timedelta(days=deleted_days_ago) if deleted_days_ago is not None else None
    return await User.create(
        email=email,
        hashed_password="x" * 60,
        name="파기",
        nickname=None,  # unique=True null=True — None 다건 허용
        phone_number="01000000000",
        birthday=date(1990, 1, 1),
        gender=Gender.MALE,
        is_active=not is_deleted,
        is_deleted=is_deleted,
        deleted_at=deleted_at,
    )


async def _create_challenge(creator: User) -> Challenge:
    today = date.today()
    return await Challenge.create(
        creator=creator,
        title="테스트 챌린지",
        category=ChallengeCategory.WATER,
        goal_type=GoalType.COUNT,
        verification_type=VerificationType.CHECK,
        start_date=today,
        end_date=today + timedelta(days=7),
    )


class TestPurgeExpiredUsers(TestCase):
    async def test_expired_deleted_user_is_purged(self):
        # 보관기간 초과(+1일) 탈퇴 유저 → 삭제됨.
        user = await _create_user("expired@example.com", deleted_days_ago=ACCOUNT_RETENTION_DAYS + 1)
        result = await purge_expired_users(dry_run=False, batch_size=100)

        assert result["total"] == 1
        assert result["purged"] == 1
        assert result["failed"] == 0
        assert await User.get_or_none(id=user.id) is None

    async def test_recently_deleted_user_is_preserved(self):
        # 보관기간 미만(1일 전) 탈퇴 유저 → 보존.
        user = await _create_user("recent@example.com", deleted_days_ago=1)
        result = await purge_expired_users(dry_run=False, batch_size=100)

        assert result["total"] == 0
        assert result["purged"] == 0
        assert await User.get_or_none(id=user.id) is not None

    async def test_boundary_exactly_at_cutoff_is_purged(self):
        # 경계: 정확히 보관기간(now - 30일) 이전이면 __lte 매치 → 삭제 대상.
        user = await _create_user("boundary@example.com", deleted_days_ago=ACCOUNT_RETENTION_DAYS)
        result = await purge_expired_users(dry_run=False, batch_size=100)

        assert result["purged"] == 1
        assert await User.get_or_none(id=user.id) is None

    async def test_active_user_is_preserved(self):
        # 정상(is_deleted=False) 유저 → 보존.
        user = await _create_user("active@example.com", is_deleted=False)
        result = await purge_expired_users(dry_run=False, batch_size=100)

        assert result["total"] == 0
        assert await User.get_or_none(id=user.id) is not None

    async def test_dry_run_deletes_nobody(self):
        # --dry-run → 대상은 집계되지만 아무도 삭제되지 않음.
        user = await _create_user("dry@example.com", deleted_days_ago=ACCOUNT_RETENTION_DAYS + 5)
        result = await purge_expired_users(dry_run=True, batch_size=100)

        assert result["total"] == 1
        assert result["purged"] == 0
        assert await User.get_or_none(id=user.id) is not None

    async def test_batching_purges_all(self):
        # batch_size 가 대상 수보다 작아도 전부 삭제된다.
        users = [
            await _create_user(f"batch{i}@example.com", deleted_days_ago=ACCOUNT_RETENTION_DAYS + 1) for i in range(5)
        ]
        result = await purge_expired_users(dry_run=False, batch_size=2)

        assert result["total"] == 5
        assert result["purged"] == 5
        for user in users:
            assert await User.get_or_none(id=user.id) is None

    async def test_challenge_survives_user_purge_with_null_creator(self):
        # 안전장치 핵심: 탈퇴 유저 파기 후에도 그가 만든 챌린지는 살아남고 creator_id=None.
        # Challenge.creator 가 SET_NULL 인 경우에만 유효한 검증이므로, CASCADE 인 환경에서는 skip.
        on_delete = Challenge._meta.fields_map["creator"].on_delete  # type: ignore[attr-defined]
        if on_delete != fields.SET_NULL:
            self.skipTest(f"Challenge.creator.on_delete={on_delete} (SET_NULL 아님) — 생존 검증 보류")

        user = await _create_user("creator@example.com", deleted_days_ago=ACCOUNT_RETENTION_DAYS + 1)
        challenge = await _create_challenge(user)

        result = await purge_expired_users(dry_run=False, batch_size=100)
        assert result["purged"] == 1

        assert await User.get_or_none(id=user.id) is None
        surviving = await Challenge.get_or_none(id=challenge.id)
        assert surviving is not None  # 챌린지는 살아남아야 함
        assert surviving.creator_id is None  # creator 만 NULL


def test_apply_flag_defaults_to_dry_run():
    # 안전 기본값: --apply 미지정이면 실삭제하지 않는다(되돌릴 수 없는 영구 삭제이므로 opt-in).
    assert parse_args([]).apply is False
    assert parse_args(["--apply"]).apply is True
