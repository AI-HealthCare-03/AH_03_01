"""주간 활동량(EXP) 시스템.

규칙
- 활동량 행위 1건 = 10 EXP.
- HEALTH_INPUT, HEALTH_VIEW 는 1일 1회 제한 (dedupe_key 로 unique 보장).
- 주간 집계는 ISO 주차(YYYY-Www) 단위. 매주 월요일 00:00(Asia/Seoul) 에 직전 주 마감.
- 마감 시 상위 3명에게 포인트 차등 지급(500/300/100) → RewardService.grant 호출.
- 마감 처리는 별도 cron 없이 첫 GET 요청 시 lazy 정산.
"""

from __future__ import annotations

from enum import StrEnum

from tortoise import fields, models


class XpKind(StrEnum):
    HEALTH_INPUT = "HEALTH_INPUT"
    HEALTH_VIEW = "HEALTH_VIEW"
    CHALLENGE_VERIFY = "CHALLENGE_VERIFY"
    POST = "POST"
    COMMENT = "COMMENT"
    QUIZ = "QUIZ"


class XpEvent(models.Model):
    """활동 1건 = 1 row. 주간 집계의 원천 데이터."""

    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="xp_events", on_delete=fields.CASCADE)
    kind = fields.CharEnumField(enum_type=XpKind, max_length=24)
    points = fields.IntField(default=10)
    week_id = fields.CharField(max_length=8, index=True)  # "2026-W20" 등
    occurred_at = fields.DatetimeField(auto_now_add=True)
    # 1일 1회 제한이 필요한 활동의 멱등키. e.g. "HEALTH_INPUT:2026-05-17"
    dedupe_key = fields.CharField(max_length=64, null=True, unique=True)

    class Meta:
        table = "xp_events"
        indexes = (("user_id", "week_id"),)


class WeeklySettlement(models.Model):
    """주차 정산 멱등 처리용. 같은 week_id 두 번 정산되지 않도록 unique."""

    id = fields.BigIntField(primary_key=True)
    week_id = fields.CharField(max_length=8, unique=True)
    settled_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "weekly_settlements"
