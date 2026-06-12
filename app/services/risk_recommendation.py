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
    MODEL_VERSION,
    PredictionSummary,
    RiskRecommendationResult,
    compute_feature_snapshot,
    run_risk_recommendation,
)
from app.models.ml_inference import MLInferenceKind, MLInferenceRequest
from app.models.risk_recommendation_result import (
    RiskRecommendationResult as RiskRecommendationResultModel,
)
from app.services import risk_recommendation_cache as cache

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
        """2-tier 캐시 게이트 (Redis 단기 + DB append-only) → (hit) 저장본 / (miss) 그래프 실행.

        세션 중 건강정보 수정이 드물다는 전제로 반복 요청 시 DB 쿼리·그래프 호출을 0회로
        만든다. 흐름(순서 엄수):
          1. ``risk:reco`` GET — 직전 성공 응답 + 그 때 쓴 snapshot/model_version 확보.
          2. 현재 snapshot 확보: ``risk:snapshot`` 히트면 **DB 미접근**, 미스면 DB read 후 캐싱.
          3. reco 히트 AND snapshot 일치 AND model_version 일치 → 저장본 즉시 반환 (그래프·DB 0).
          4. 미스/불일치 → throttle → 그래프 실행 → 저장 가드 통과 시 DB append + Redis SET.
        Redis 장애는 best-effort 로 흡수하고 DB/그래프 경로로 폴백한다 (진실 원본은 DB).
        (cache hit 시 throttle 미적용 — 무비용 경로.)
        """
        cached_reco = await cache.get_reco(user_id)

        # 2. 현재 snapshot 확보 — Redis 히트면 DB 미접근, 미스면 DB read 후 캐싱.
        current_snapshot = await cache.get_snapshot(user_id)
        if current_snapshot is None:
            current_snapshot = await compute_feature_snapshot(user_id)
            if current_snapshot is not None:
                await cache.set_snapshot(user_id, current_snapshot)

        # 3. reco 히트 + 입력/모델 버전 일치 → 저장본 즉시 반환 (그래프·DB 0회).
        #    필수데이터 없음(snapshot None)이면 캐시 비교 생략하고 그래프(missing-info) 경로.
        if (
            current_snapshot is not None
            and cached_reco is not None
            and cached_reco.get("model_version") == MODEL_VERSION
            and cached_reco.get("snapshot") == current_snapshot
        ):
            response = cached_reco.get("response")
            if isinstance(response, dict):
                return RiskRecommendationResponse(**response)

        # 4. 미스/불일치 → throttle → 그래프 실행 → 저장 가드 통과 시 DB append + Redis SET.
        await self._enforce_throttle(user_id)
        result: RiskRecommendationResult = await run_risk_recommendation(user_id=user_id)
        response = _to_response(result)

        # fallback / 데이터 미충족 결과는 캐싱하지 않음 (다음 호출에 재시도 가능해야 함).
        if result.has_required_data and not result.is_fallback:
            await self._save_cache(user_id, result)
            await cache.set_reco(
                user_id,
                snapshot=result.feature_snapshot,
                model_version=result.model_version,
                response=response.model_dump(mode="json"),
            )
            await cache.set_snapshot(user_id, result.feature_snapshot)

        return response

    @staticmethod
    async def _save_cache(user_id: Any, result: RiskRecommendationResult) -> None:
        """위험도 권고 결과 한 행을 이력에 append insert (append-only, 다수 row/user)."""
        await RiskRecommendationResultModel.create(
            user_id=user_id,
            input_snapshot=result.feature_snapshot,
            model_version=result.model_version,
            answer=result.answer,
            tips=list(result.tips),
            diet=list(result.diet),
            sources=[_source_to_dict(s) for s in result.sources],
            predictions=[_prediction_to_dict(p) for p in result.predictions],
            is_fallback=result.is_fallback,
            eval_revision_count=result.eval_revision_count,
        )

    @staticmethod
    async def _enforce_throttle(user_id: Any) -> None:
        """동일 사용자의 직전 호출 시각과의 간격을 검사 (60s 쿨다운).

        쿨다운 위반 시 429 + Retry-After 헤더. ml_inference_requests 의 created_at
        을 시계열 기준으로 사용 — 그래프가 row 를 가장 먼저 만들기 때문에 노드
        중간 실패 케이스에서도 일관됨.
        """
        latest = (
            await MLInferenceRequest.filter(user_id=user_id, kind=MLInferenceKind.RISK_PREDICTION)
            .order_by("-created_at")
            .only("created_at")
            .first()
        )
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
        recommended_tips=list(r.tips),
        recommended_diet=list(r.diet),
        has_required_data=r.has_required_data,
        missing_fields=list(r.missing_fields),
        action_hint=("navigate_to_health_info" if not r.has_required_data else None),
        is_fallback=r.is_fallback,
        eval_revision_count=r.eval_revision_count,
        disclaimer=r.disclaimer,
        model_version=r.model_version,
    )


def _source_to_dict(c: Any) -> dict[str, Any]:
    """RetrievedChunk → 캐시/응답 공용 dict (RecommendationSourceItem 필드와 동형)."""
    text = getattr(c, "chunk_text", "") or ""
    snippet = text[:_SNIPPET_MAX_LEN] + ("…" if len(text) > _SNIPPET_MAX_LEN else "")
    return {
        "title": getattr(c, "title", None),
        "document_id": getattr(c, "document_id", None),
        "snippet": snippet,
        "source": getattr(c, "source", None),
    }


def _prediction_to_dict(p: PredictionSummary) -> dict[str, Any]:
    """PredictionSummary → 캐시 dict (RiskPredictionItem 필드와 동형)."""
    return {
        "disease_type": p.disease_type,
        "risk_score": p.risk_score,
        "risk_level": p.risk_level,
        "contributing_factors": list(p.contributing_factors),
    }


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
