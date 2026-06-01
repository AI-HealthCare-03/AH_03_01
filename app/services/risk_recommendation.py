"""RiskRecommendationService — RiskRecommendationGraph 실행 + DTO 매핑.

라우터는 본 서비스 한 메서드(`recommend(user_id)`)만 호출. 그래프 결과를
`RiskRecommendationResponse` Pydantic 모델로 변환해 응답 직렬화.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.dtos.risk_recommendation import (
    ContributingFactorItem,
    RecommendationSourceItem,
    RiskPredictionItem,
    RiskRecommendationResponse,
)
from app.graphs.risk_recommendation_graph import (
    PredictionSummary,
    RiskRecommendationResult,
    run_risk_recommendation,
)
from app.models.ml_inference import MLInferenceRequest

_SNIPPET_MAX_LEN = 200  # 출처 카드용 본문 발췌 길이

# H-4: 사용자별 throttle. 한 호출당 DB 6 row + OpenAI 2~3회로 비용·법적 노출이
# 결합돼 있어 짧은 간격 반복 호출을 차단. 마지막 ml_inference_requests row 의
# created_at 기준 — 호출 자체가 RUNNING/SUCCESS 인지 무관하게 시계열 기반.
_THROTTLE_COOLDOWN_SEC = 60.0


class RiskRecommendationService:
    """라우터 의존성 주입 단위.

    상태가 없는 thin wrapper. FastAPI `Depends(RiskRecommendationService)` 가 매 요청마다
    인스턴스화.
    """

    async def recommend(self, *, user_id: Any) -> RiskRecommendationResponse:
        """그래프 실행 + Pydantic 응답 모델로 매핑."""
        await self._enforce_throttle(user_id)
        result: RiskRecommendationResult = await run_risk_recommendation(user_id=user_id)
        return _to_response(result)

    @staticmethod
    async def _enforce_throttle(user_id: Any) -> None:
        """동일 사용자의 직전 호출 시각과의 간격을 검사 (60s 쿨다운).

        쿨다운 위반 시 429 + Retry-After 헤더. ml_inference_requests 의 created_at
        을 시계열 기준으로 사용 — 그래프가 row 를 가장 먼저 만들기 때문에 노드
        중간 실패 케이스에서도 일관됨.
        """
        latest = await MLInferenceRequest.filter(user_id=user_id).order_by("-created_at").only("created_at").first()
        if latest is None:
            return
        elapsed = (datetime.now(tz=UTC) - latest.created_at).total_seconds()
        if elapsed < _THROTTLE_COOLDOWN_SEC:
            retry_after = max(1, math.ceil(_THROTTLE_COOLDOWN_SEC - elapsed))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"잠시 후 다시 시도해 주세요. (쿨다운 {_THROTTLE_COOLDOWN_SEC:.0f}s)",
                headers={"Retry-After": str(retry_after)},
            )


def _to_response(r: RiskRecommendationResult) -> RiskRecommendationResponse:
    return RiskRecommendationResponse(
        answer=r.answer,
        predictions=[_to_prediction_item(p) for p in r.predictions],
        sources=[_to_source_item(c) for c in r.sources],
        has_required_data=r.has_required_data,
        missing_fields=list(r.missing_fields),
        action_hint=("navigate_to_health_info" if not r.has_required_data else None),
        is_fallback=r.is_fallback,
        eval_revision_count=r.eval_revision_count,
        disclaimer=r.disclaimer,
        model_version=r.model_version,
    )


def _to_prediction_item(p: PredictionSummary) -> RiskPredictionItem:
    return RiskPredictionItem(
        disease_type=p.disease_type,
        risk_score=p.risk_score,
        risk_level=p.risk_level,
        contributing_factors=[ContributingFactorItem(**f) for f in p.contributing_factors],
    )


def _to_source_item(c: Any) -> RecommendationSourceItem:
    """RetrievedChunk → RecommendationSourceItem."""
    text = getattr(c, "chunk_text", "") or ""
    snippet = text[:_SNIPPET_MAX_LEN] + ("…" if len(text) > _SNIPPET_MAX_LEN else "")
    return RecommendationSourceItem(
        title=getattr(c, "title", None),
        document_id=getattr(c, "document_id", None),
        snippet=snippet,
        source=getattr(c, "source", None),
    )
