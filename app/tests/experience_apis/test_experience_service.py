"""주간 활동량(EXP) 서비스 로직 검증.

- HEALTH_INPUT/HEALTH_VIEW 1일 1회 멱등 (유저별, 일자/주차 Asia/Seoul 기준)
- CHALLENGE_VERIFY/POST/COMMENT/QUIZ 는 행위마다 누적
- 주간 경계(ISO 주차, Asia/Seoul) + 주차 정산 멱등성/보상 지급
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from tortoise.contrib.test import TestCase

from app.models.experience import XpEvent, XpKind
from app.models.pet import PointTransaction
from app.models.users import User
from app.services.experience import (
    ExperienceService,
    current_week_id,
    previous_week_id,
)

SEOUL = ZoneInfo("Asia/Seoul")


async def _mk_user(email: str) -> User:
    return await User.create(
        email=email,
        hashed_password="x",
        name="활동이",
        nickname=email[:8],
        gender="MALE",
        birthday="1990-01-01",
        phone_number="0100000",
    )


class TestOncePerDay(TestCase):
    async def test_health_view_deduped_same_day(self):
        u = await _mk_user("view1@e.com")
        svc = ExperienceService()
        first = await svc.award(user_id=u.id, kind=XpKind.HEALTH_VIEW)
        second = await svc.award(user_id=u.id, kind=XpKind.HEALTH_VIEW)
        assert first is not None
        assert second is None  # 같은 날 2번째는 멱등 차단
        assert await XpEvent.filter(user_id=u.id, kind=XpKind.HEALTH_VIEW).count() == 1

    async def test_health_input_deduped_same_day(self):
        u = await _mk_user("input1@e.com")
        svc = ExperienceService()
        await svc.award(user_id=u.id, kind=XpKind.HEALTH_INPUT)
        await svc.award(user_id=u.id, kind=XpKind.HEALTH_INPUT)
        assert await XpEvent.filter(user_id=u.id, kind=XpKind.HEALTH_INPUT).count() == 1

    async def test_input_and_view_are_independent(self):
        # 입력과 확인은 각각 1일 1회 (서로 별개로 누적)
        u = await _mk_user("iv1@e.com")
        svc = ExperienceService()
        await svc.award(user_id=u.id, kind=XpKind.HEALTH_INPUT)
        await svc.award(user_id=u.id, kind=XpKind.HEALTH_VIEW)
        assert await XpEvent.filter(user_id=u.id).count() == 2

    async def test_dedupe_is_per_user(self):
        # 한 유저가 적립해도 다른 유저는 막히면 안 됨 (dedupe_key 에 user_id 포함)
        a = await _mk_user("pu_a@e.com")
        b = await _mk_user("pu_b@e.com")
        svc = ExperienceService()
        ra = await svc.award(user_id=a.id, kind=XpKind.HEALTH_VIEW)
        rb = await svc.award(user_id=b.id, kind=XpKind.HEALTH_VIEW)
        assert ra is not None and rb is not None
        assert await XpEvent.filter(user_id=a.id).count() == 1
        assert await XpEvent.filter(user_id=b.id).count() == 1


class TestRepeatableKinds(TestCase):
    async def test_challenge_verify_accumulates_each_time(self):
        u = await _mk_user("rep1@e.com")
        svc = ExperienceService()
        for _ in range(3):
            assert await svc.award(user_id=u.id, kind=XpKind.CHALLENGE_VERIFY) is not None
        assert await XpEvent.filter(user_id=u.id, kind=XpKind.CHALLENGE_VERIFY).count() == 3

    async def test_post_comment_quiz_accumulate(self):
        u = await _mk_user("rep2@e.com")
        svc = ExperienceService()
        for kind in (XpKind.POST, XpKind.COMMENT, XpKind.QUIZ):
            await svc.award(user_id=u.id, kind=kind)
            await svc.award(user_id=u.id, kind=kind)
        # 3종 x 2회 = 6 (행위마다 누적)
        assert await XpEvent.filter(user_id=u.id).count() == 6


class TestWeeklyBoundary(TestCase):
    def test_iso_week_id_seoul(self):
        # 월요일 00:00 KST 에 새 주차 시작 (ISO, Asia/Seoul)
        assert current_week_id(datetime(2026, 6, 8, 0, 0, tzinfo=SEOUL)) == "2026-W24"
        assert current_week_id(datetime(2026, 6, 7, 23, 59, tzinfo=SEOUL)) == "2026-W23"

    def test_previous_week_id(self):
        assert previous_week_id(datetime(2026, 6, 8, 0, 0, tzinfo=SEOUL)) == "2026-W23"
        # ISO 연도 경계
        assert previous_week_id(datetime(2026, 1, 1, 12, 0, tzinfo=SEOUL)) == "2025-W52"

    async def test_summary_scoped_to_current_week_resets(self):
        # "리셋" = 주차 경계 넘으면 week_id 가 바뀌어 집계에서 빠짐 (쿼리 시 주간 필터)
        u = await _mk_user("wk1@e.com")
        svc = ExperienceService()
        await svc.award(user_id=u.id, kind=XpKind.CHALLENGE_VERIFY)
        await svc.award(user_id=u.id, kind=XpKind.POST)
        summary = await svc.get_weekly_summary(user_id=u.id)
        assert summary.week_id == current_week_id()
        assert summary.total_points == 20  # 이번 주 누적

        # 지난 주차에 속하는 이벤트는 이번 주 집계에 포함되지 않음 → 사실상 리셋
        await XpEvent.create(
            user_id=u.id,
            kind=XpKind.POST,
            points=10,
            week_id=previous_week_id(),
            dedupe_key=None,
        )
        summary2 = await svc.get_weekly_summary(user_id=u.id)
        assert summary2.total_points == 20  # 지난 주 이벤트는 안 잡힘


class TestSettlement(TestCase):
    async def test_settlement_is_idempotent(self):
        u = await _mk_user("set1@e.com")
        svc = ExperienceService()
        await svc.award(user_id=u.id, kind=XpKind.CHALLENGE_VERIFY)
        wk = current_week_id()
        assert await svc.settle_week_if_needed(week_id=wk) is True
        assert await svc.settle_week_if_needed(week_id=wk) is False  # 두 번째는 멱등 차단

    async def test_settlement_grants_points_to_winner(self):
        # 회귀: settle 내부 int(uuid) 캐스트 버그로 보상이 조용히 누락되던 케이스
        u = await _mk_user("win1@e.com")
        svc = ExperienceService()
        await svc.award(user_id=u.id, kind=XpKind.CHALLENGE_VERIFY)
        wk = current_week_id()
        await svc.settle_week_if_needed(week_id=wk)
        assert await PointTransaction.filter(user_id=u.id).count() == 1


class TestLeaderboard(TestCase):
    async def test_leaderboard_ranks_and_my_rank(self):
        svc = ExperienceService()
        high = await _mk_user("lb_hi@e.com")
        low = await _mk_user("lb_lo@e.com")
        for _ in range(3):
            await svc.award(user_id=high.id, kind=XpKind.CHALLENGE_VERIFY)
        await svc.award(user_id=low.id, kind=XpKind.CHALLENGE_VERIFY)
        result = await svc.get_leaderboard(my_user_id=low.id, limit=10)
        assert result.entries[0].user_id == high.id
        assert result.entries[0].points == 30
        assert result.my_rank == 2
        assert result.my_points == 10
