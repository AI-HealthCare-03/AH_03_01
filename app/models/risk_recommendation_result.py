"""RiskRecommendationResult — RAG 위험도 권고 그래프 결과 이력 (append-only).

`POST /api/v1/risk-recommendations` 가 매 호출마다 ML 추론(질환 3종) + OpenAI LLM 2~3회를
실행하므로 비용·지연이 크다. 동일 입력(모델 입력 snapshot) + 동일 model_version 이면
결과가 결정적으로 같으므로, 직전 성공 결과를 캐싱해 재호출을 회피한다.

서빙 캐시는 Redis 단기 캐시(`risk_recommendation_cache`)가 담당하고, 본 테이블은
추이/통계/백업용 **append-only 이력**(사용자당 다수 row)이다. 그래프가 새로 실행돼
저장 가드(has_required_data AND not is_fallback)를 통과할 때마다 한 행을 insert 한다.
(user_id, created_at) 인덱스로 최신본·추이 조회를 가속한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class RiskRecommendationResult(models.Model):
    """사용자별 위험도 권고 그래프 결과 이력 (append-only, 다수 row/user)."""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="risk_recommendation_results",
        on_delete=fields.CASCADE,
    )
    user_id: Any
    # 캐시 비교 기준 — PredictionInput.snapshot() (26필드 + age/gender, 레코드 폴백 반영값)
    input_snapshot: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    model_version = fields.CharField(max_length=40, default="risk-graph-v1")
    # 그래프 출력 (영속 이력)
    answer = fields.TextField(default="")
    tips: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    diet: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    sources: list[dict[str, Any]] = fields.JSONField(default=list)  # type: ignore[assignment]
    predictions: list[dict[str, Any]] = fields.JSONField(default=list)  # type: ignore[assignment]
    # 프론트 카드용 구조화 추천 챌린지 (template_id/title/category/difficulty/reason/priority)
    recommended_challenges: list[dict[str, Any]] = fields.JSONField(default=list)  # type: ignore[assignment]
    is_fallback = fields.BooleanField(default=False)
    eval_revision_count = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "risk_recommendation_results"
        # 추이/통계 + 최신본 조회 가속 (user 별 시계열).
        indexes = (("user_id", "created_at"),)
