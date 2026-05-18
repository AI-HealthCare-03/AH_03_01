"""주간 활동량 EXP 적립 + 주간 리더보드 정산.

핵심 API
- award(user_id, kind): 10 EXP 적립. HEALTH_INPUT/HEALTH_VIEW 는 1일 1회 멱등.
- get_weekly_summary(user_id): 이번 주(현재 ISO 주차) 누적 + breakdown.
- get_leaderboard(week_id, my_user_id): 상위 N + my rank.
- settle_week_if_needed(week_id): 정산 (상위 3명에게 500/300/100 포인트 지급).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tortoise.exceptions import IntegrityError
from tortoise.functions import Sum

from app.models.experience import WeeklySettlement, XpEvent, XpKind
from app.models.pet import PointSource
from app.services.rewards import RewardService

SEOUL = ZoneInfo("Asia/Seoul")

# 활동별 EXP. 사양상 일괄 10.
XP_PER_EVENT = 10

# 1일 1회 제한 활동
_ONCE_PER_DAY_KINDS = {XpKind.HEALTH_INPUT, XpKind.HEALTH_VIEW}

# 상위 3명 포인트 보상
WEEKLY_RANK_REWARDS = (500, 300, 100)


def current_week_id(now: datetime | None = None) -> str:
    """현재(또는 주어진) 시각의 ISO 주차 ID. e.g. '2026-W20'."""
    now = now or datetime.now(SEOUL)
    if now.tzinfo is None:
        now = now.replace(tzinfo=SEOUL)
    iso = now.astimezone(SEOUL).isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def previous_week_id(now: datetime | None = None) -> str:
    """직전 주 ID. 정산 대상 산정용."""
    now = now or datetime.now(SEOUL)
    if now.tzinfo is None:
        now = now.replace(tzinfo=SEOUL)
    iso_now = now.astimezone(SEOUL)
    monday = iso_now - (iso_now - iso_now.replace(hour=0, minute=0, second=0, microsecond=0))
    # 단순화: now - 7일.
    prev = iso_now.timestamp() - 7 * 86400
    return current_week_id(datetime.fromtimestamp(prev, tz=SEOUL))


def _today_dedupe_key(kind: XpKind) -> str:
    today = datetime.now(SEOUL).date().isoformat()
    return f"{kind.value}:{today}"


@dataclass(slots=True)
class WeeklyBreakdownItem:
    kind: str
    count: int
    points: int


@dataclass(slots=True)
class WeeklySummary:
    week_id: str
    total_points: int
    items: list[WeeklyBreakdownItem]


@dataclass(slots=True)
class LeaderboardEntry:
    user_id: int
    user_name: str
    points: int
    rank: int


@dataclass(slots=True)
class LeaderboardResult:
    week_id: str
    entries: list[LeaderboardEntry]
    my_rank: int | None
    my_points: int


class ExperienceService:
    def __init__(self) -> None:
        self.reward_service = RewardService()

    async def award(self, *, user_id: int, kind: XpKind) -> XpEvent | None:
        """활동 EXP 적립. 1일 1회 제한 활동은 중복 시 None 반환."""
        week_id = current_week_id()
        dedupe_key = _today_dedupe_key(kind) if kind in _ONCE_PER_DAY_KINDS else None
        # HEALTH_INPUT/VIEW 는 user 별로도 dedupe 필요 — kind:date:user_id 로 구성.
        if dedupe_key is not None:
            dedupe_key = f"{dedupe_key}:{user_id}"
        try:
            return await XpEvent.create(
                user_id=user_id,
                kind=kind,
                points=XP_PER_EVENT,
                week_id=week_id,
                dedupe_key=dedupe_key,
            )
        except IntegrityError:
            return None  # 이미 오늘 적립됨

    async def get_weekly_summary(self, *, user_id: int) -> WeeklySummary:
        week_id = current_week_id()
        events = await XpEvent.filter(user_id=user_id, week_id=week_id).all()
        breakdown: dict[str, WeeklyBreakdownItem] = {}
        total = 0
        for ev in events:
            kv = ev.kind.value if hasattr(ev.kind, "value") else str(ev.kind)
            item = breakdown.setdefault(kv, WeeklyBreakdownItem(kind=kv, count=0, points=0))
            item.count += 1
            item.points += ev.points
            total += ev.points
        # 정의된 순서로 정렬
        order = [k.value for k in XpKind]
        ordered = sorted(breakdown.values(), key=lambda i: order.index(i.kind) if i.kind in order else 99)
        return WeeklySummary(week_id=week_id, total_points=total, items=ordered)

    async def get_leaderboard(
        self,
        *,
        week_id: str | None = None,
        my_user_id: int,
        limit: int = 10,
    ) -> LeaderboardResult:
        week_id = week_id or current_week_id()
        rows = (
            await XpEvent.filter(week_id=week_id)
            .annotate(total=Sum("points"))
            .group_by("user_id")
            .values("user_id", "total")
        )
        # 정렬
        rows_sorted = sorted(rows, key=lambda r: r["total"] or 0, reverse=True)
        # user name lookup
        from app.models.users import User
        users_map = {u.id: u.name for u in await User.filter(id__in=[r["user_id"] for r in rows_sorted]).all()}

        entries: list[LeaderboardEntry] = []
        my_rank: int | None = None
        my_points = 0
        for idx, r in enumerate(rows_sorted, start=1):
            uid = int(r["user_id"])
            pts = int(r["total"] or 0)
            if uid == my_user_id:
                my_rank = idx
                my_points = pts
            if idx <= limit:
                entries.append(
                    LeaderboardEntry(
                        user_id=uid,
                        user_name=users_map.get(uid, f"user-{uid}"),
                        points=pts,
                        rank=idx,
                    )
                )
        return LeaderboardResult(week_id=week_id, entries=entries, my_rank=my_rank, my_points=my_points)

    async def settle_week_if_needed(self, *, week_id: str) -> bool:
        """주차 정산. 멱등성 보장. True = 이번 호출에서 정산함."""
        try:
            await WeeklySettlement.create(week_id=week_id)
        except IntegrityError:
            return False  # 이미 정산됨

        # 상위 3명 산출
        rows = (
            await XpEvent.filter(week_id=week_id)
            .annotate(total=Sum("points"))
            .group_by("user_id")
            .values("user_id", "total")
        )
        rows_sorted = sorted(rows, key=lambda r: r["total"] or 0, reverse=True)[: len(WEEKLY_RANK_REWARDS)]

        for idx, r in enumerate(rows_sorted):
            uid = int(r["user_id"])
            amount = WEEKLY_RANK_REWARDS[idx]
            try:
                await self.reward_service.grant(
                    user_id=uid,
                    amount=amount,
                    source=PointSource.CHALLENGE_WEEKLY_RANK,
                    source_id=None,
                    description=f"{week_id} 주간 활동량 {idx + 1}위 보상",
                )
            except Exception:
                # 한 명 실패해도 다음 진행. 운영 로그로 후처리.
                continue
        return True
