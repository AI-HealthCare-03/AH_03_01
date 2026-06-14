"""RiskRecommendationService — RiskRecommendationGraph 실행 + DTO 매핑.

라우터는 본 서비스 한 메서드(`recommend(user_id)`)만 호출. 그래프 결과를
`RiskRecommendationResponse` Pydantic 모델로 변환해 응답 직렬화.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from tortoise.exceptions import DBConnectionError, OperationalError

from app.dtos.risk_recommendation import (
    ContributingFactorItem,
    RecommendationSourceItem,
    RecommendedChallengeItem,
    RiskPredictionItem,
    RiskRecommendationResponse,
)
from app.graphs.risk_recommendation_graph import (
    MODEL_VERSION,
    STAGE_LABELS,
    PredictionSummary,
    RecommendedChallenge,
    RiskRecommendationResult,
    compute_feature_snapshot,
    run_risk_recommendation,
    run_risk_recommendation_stream,
)
from app.models.ml_inference import MLInferenceKind, MLInferenceRequest
from app.models.risk_recommendation_result import (
    RiskRecommendationResult as RiskRecommendationResultModel,
)
from app.services import risk_recommendation_cache as cache

logger = logging.getLogger(__name__)

_SNIPPET_MAX_LEN = 200  # 출처 카드용 본문 발췌 길이

# H-4: 사용자별 throttle. 한 호출당 DB 6 row + OpenAI 2~3회로 비용·법적 노출이
# 결합돼 있어 짧은 간격 반복 호출을 차단. 마지막 ml_inference_requests row 의
# created_at 기준 — 호출 자체가 RUNNING/SUCCESS 인지 무관하게 시계열 기반.
_THROTTLE_COOLDOWN_SEC = 60.0

_TOKEN_CHUNK_SIZE = 12  # done 직전 answer 를 청크로 흘릴 때 한 토큰 길이 (한글 가독성, 챗봇 스트림과 동일)


def _sse(event: str, data: dict[str, Any]) -> str:
    """SSE 프레임 직렬화 — `event: <type>\\ndata: <json>\\n\\n` (JSON ensure_ascii=False). 직렬화는 이 한 곳."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _iter_token_chunks(text: str) -> list[str]:
    """answer 문자열을 _TOKEN_CHUNK_SIZE 자 청크 리스트로 분할 (빈 문자열이면 빈 리스트)."""
    if not text:
        return []
    return [text[i : i + _TOKEN_CHUNK_SIZE] for i in range(0, len(text), _TOKEN_CHUNK_SIZE)]


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
        # 건강데이터 read + 그래프 실행은 DB 입력 경로. DB 연결/조회 장애 시 raw 500 이나
        # 일반 fallback 으로 가리지 않고 503(일시 오류)로 명확히 안내한다. (입력 미충족과 구분 —
        # 미충족은 그래프가 정상 missing-info 응답으로 처리.)
        try:
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
        except (DBConnectionError, OperationalError) as exc:
            logger.error("위험도 권고 DB 접근 실패 (user=%s): %s", user_id, exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="일시적으로 건강 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.",
            ) from exc

        return await self._finalize(user_id, result)

    async def recommend_stream(  # noqa: C901 — SSE 단계별(meta/stage/token/done/error) 선형 흐름
        self, *, user_id: Any
    ) -> AsyncGenerator[str, None]:
        """SSE 스트리밍 — meta → stage* → token* → done (실패 시 error) 프레임을 yield.

        비스트림 recommend() 와 동일한 캐시 게이트·throttle·저장 정책을 따르되, 그래프 진행
        단계(astream_events)를 실시간으로 흘려보낸다. done payload 는 recommend() 응답과 동일 shape.

        ⚠️ 스트림 시작(첫 yield) 후엔 HTTP status 를 바꿀 수 없으므로, recommend() 가 503/429 로
        내던 DB 장애·throttle 위반은 여기선 error 이벤트로 전달한다.
        """
        # 1. 캐시 게이트 — 히트 시 meta + done(저장본) 즉시. (가짜 stage 없음.)
        try:
            cached_reco = await cache.get_reco(user_id)
            current_snapshot = await cache.get_snapshot(user_id)
            if current_snapshot is None:
                current_snapshot = await compute_feature_snapshot(user_id)
                if current_snapshot is not None:
                    await cache.set_snapshot(user_id, current_snapshot)
            if (
                current_snapshot is not None
                and cached_reco is not None
                and cached_reco.get("model_version") == MODEL_VERSION
                and cached_reco.get("snapshot") == current_snapshot
            ):
                cached_response = cached_reco.get("response")
                if isinstance(cached_response, dict):
                    yield _sse("meta", {"cached": True})
                    yield _sse("done", cached_response)
                    return
            await self._enforce_throttle(user_id)
        except (DBConnectionError, OperationalError) as exc:
            logger.error("위험도 권고 스트리밍 DB 접근 실패 (user=%s): %s", user_id, exc)
            yield _sse("error", {"message": "일시적으로 건강 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요."})
            return
        except HTTPException as exc:  # throttle 429 — 스트림에선 error 이벤트로 변환.
            detail = exc.detail if isinstance(exc.detail, str) else "잠시 후 다시 시도해 주세요."
            yield _sse("error", {"message": detail, "code": "THROTTLED"})
            return

        yield _sse("meta", {"cached": False})

        # 2. 그래프 스트리밍 — 노드 진입마다 stage. result 캡처.
        result: RiskRecommendationResult | None = None
        try:
            async for kind, payload in run_risk_recommendation_stream(user_id=user_id):
                if kind == "stage":
                    label = STAGE_LABELS.get(payload)
                    if label is not None:
                        yield _sse("stage", {"node": payload, "label": label})
                elif kind == "result":
                    result = payload
        except (DBConnectionError, OperationalError) as exc:
            logger.error("위험도 권고 스트리밍 그래프 DB 장애 (user=%s): %s", user_id, exc)
            yield _sse("error", {"message": "일시적으로 건강 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요."})
            return
        except Exception:  # noqa: BLE001 — 그래프 예외는 error 이벤트로 흡수
            logger.exception("위험도 권고 스트리밍 그래프 실패 (user=%s)", user_id)
            yield _sse("error", {"message": "위험도 분석 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요."})
            return

        if result is None:
            yield _sse("error", {"message": "위험도 분석 결과를 받지 못했어요. 잠시 후 다시 시도해 주세요."})
            return

        # 3. 저장(best-effort) + token + done — recommend() 와 동일 후처리.
        response = await self._finalize(user_id, result)
        for chunk in _iter_token_chunks(response.answer):
            yield _sse("token", {"text": chunk})
        yield _sse("done", response.model_dump(mode="json"))

    async def _finalize(self, user_id: Any, result: RiskRecommendationResult) -> RiskRecommendationResponse:
        """그래프 결과 → 응답 매핑 + 저장(가드 통과 시 DB append best-effort + Redis SET). 공용 후처리."""
        response = _to_response(result)
        # fallback / 데이터 미충족 결과는 캐싱하지 않음 (다음 호출에 재시도 가능해야 함).
        if result.has_required_data and not result.is_fallback:
            # DB append 는 best-effort — 이력 저장이 실패해도 이미 산출된 유효 결과는 반환한다.
            # (여기서 500 을 내면 비용을 치른 LLM 결과를 버리고, 캐시도 못 채워 재호출이 반복됨.)
            try:
                await self._save_cache(user_id, result)
            except Exception as exc:  # noqa: BLE001 — 이력 적재 실패는 응답을 막지 않는다
                logger.warning("위험도 권고 DB 저장 실패, 이력 스킵 (user=%s): %s", user_id, exc)
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
            recommended_challenges=[_challenge_to_dict(c) for c in result.recommended_challenges],
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
        recommended_challenges=[_to_challenge_item(c) for c in r.recommended_challenges],
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


def _to_challenge_item(c: RecommendedChallenge) -> RecommendedChallengeItem:
    """RecommendedChallenge → RecommendedChallengeItem (응답 DTO)."""
    return RecommendedChallengeItem(
        template_id=c.template_id,
        title=c.title,
        category=c.category,
        difficulty=c.difficulty,
        reason=c.reason,
        priority=c.priority,
    )


def _challenge_to_dict(c: RecommendedChallenge) -> dict[str, Any]:
    """RecommendedChallenge → 이력 저장 dict (RecommendedChallengeItem 필드와 동형)."""
    return {
        "template_id": c.template_id,
        "title": c.title,
        "category": c.category,
        "difficulty": c.difficulty,
        "reason": c.reason,
        "priority": c.priority,
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
