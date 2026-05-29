"""RiskRecommendationService — RiskRecommendationGraph 실행 + DTO 매핑.

라우터는 본 서비스 한 메서드(`recommend(user_id)`)만 호출. 그래프 결과를
`RiskRecommendationResponse` Pydantic 모델로 변환해 응답 직렬화.
"""

from __future__ import annotations

from typing import Any

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

_SNIPPET_MAX_LEN = 200  # 출처 카드용 본문 발췌 길이


class RiskRecommendationService:
    """라우터 의존성 주입 단위.

    상태가 없는 thin wrapper. FastAPI `Depends(RiskRecommendationService)` 가 매 요청마다
    인스턴스화. 향후 캐싱/throttle 정책을 여기에 추가할 수 있다.
    """

    async def recommend(self, *, user_id: Any) -> RiskRecommendationResponse:
        """그래프 실행 + Pydantic 응답 모델로 매핑."""
        result: RiskRecommendationResult = await run_risk_recommendation(user_id=user_id)
        return _to_response(result)


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
