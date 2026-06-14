"""RiskRecommendationService.recommend() 의 DB 장애 처리 단위 테스트.

- READ 경로(snapshot 산출 / 그래프 실행)의 DB 연결·조회 장애 → 503 (입력 미충족과 구분).
- 이력 저장(_save_cache, WRITE) 실패 → best-effort: 이미 산출된 유효 결과는 반환하고
  Redis set 은 그대로 실행돼 "DB 실패 → 캐시 미적재 → LLM 재호출 반복" 루프를 끊는다.

실 DB·LLM 의존 없이 서비스 의존성만 모킹한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, status
from tortoise.exceptions import DBConnectionError, OperationalError

from app.graphs.risk_recommendation_graph import (
    RecommendedChallenge,
    RiskRecommendationResult,
    _join_recommended_challenges,
)
from app.services.ml.challenge_eligibility_filter import EligibleTemplate
from app.services.risk_recommendation import RiskRecommendationService, _to_response

_MOD = "app.services.risk_recommendation"
_CACHE = "app.services.risk_recommendation_cache"
_USER_ID = "00000000-0000-0000-0000-000000000001"


def _valid_result() -> RiskRecommendationResult:
    return RiskRecommendationResult(
        answer="권고 본문",
        predictions=[],
        sources=[],
        has_required_data=True,
        is_fallback=False,
        feature_snapshot={"age": 50},
    )


def _eligible(template_id: int, title: str = "주 5일 30분 걷기") -> EligibleTemplate:
    from app.models.challenge import RecommendationPriority

    return EligibleTemplate(
        template_id=template_id,
        category="EXERCISE",
        sub_category="WALKING",
        title=title,
        difficulty="LEVEL_1",
        priority_hint=RecommendationPriority.TOP,
    )


def test_join_recommended_challenges_joins_meta_by_template_id() -> None:
    """state.recommended_challenges(id/priority/reason) + eligible_templates(메타) → 구조화 카드."""
    state = {
        "recommended_challenges": [
            {"template_id": 7, "priority": "TOP", "reason": "혈압 관리 핵심"},
            {"template_id": 99, "priority": "OPTIONAL", "reason": "카탈로그 외 — 제외돼야 함"},
            {"priority": "TOP", "reason": "id 없음 — 제외"},
        ],
        "eligible_templates": [_eligible(7)],
    }
    out = _join_recommended_challenges(state)  # type: ignore[arg-type]
    assert len(out) == 1
    item = out[0]
    assert item.template_id == 7
    assert item.title == "주 5일 30분 걷기"
    assert item.category == "EXERCISE"
    assert item.difficulty == "LEVEL_1"
    assert item.reason == "혈압 관리 핵심"
    assert item.priority == "TOP"


def test_join_recommended_challenges_empty_when_no_selection() -> None:
    """LLM 미선정(빈 recommended_challenges) → 빈 리스트."""
    assert _join_recommended_challenges({"recommended_challenges": [], "eligible_templates": [_eligible(7)]}) == []  # type: ignore[arg-type]


def test_to_response_serializes_recommended_challenges() -> None:
    """결과의 recommended_challenges 가 응답 DTO(JSON) 에 키·타입대로 직렬화된다."""
    result = RiskRecommendationResult(
        answer="권고 본문",
        recommended_challenges=[
            RecommendedChallenge(
                template_id=7,
                title="주 5일 30분 걷기",
                category="EXERCISE",
                difficulty="LEVEL_1",
                reason="혈압 관리 핵심",
                priority="TOP",
            )
        ],
    )
    payload = _to_response(result).model_dump(mode="json")
    assert payload["recommended_challenges"] == [
        {
            "template_id": 7,
            "title": "주 5일 30분 걷기",
            "category": "EXERCISE",
            "difficulty": "LEVEL_1",
            "reason": "혈압 관리 핵심",
            "priority": "TOP",
        }
    ]


@pytest.mark.parametrize("db_exc", [DBConnectionError("db down"), OperationalError("db down")])
async def test_db_error_on_snapshot_read_returns_503(db_exc: Exception) -> None:
    """snapshot 산출(compute_feature_snapshot) DB 장애 → 503."""
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=None)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value=None)),
        patch(f"{_MOD}.compute_feature_snapshot", AsyncMock(side_effect=db_exc)),
        pytest.raises(HTTPException) as exc_info,
    ):
        await RiskRecommendationService().recommend(user_id=_USER_ID)
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


async def test_db_error_in_graph_returns_503() -> None:
    """그래프 실행(run_risk_recommendation) DB 장애 → 503 (fallback 으로 가리지 않음)."""
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=None)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value=None)),
        patch(f"{_MOD}.compute_feature_snapshot", AsyncMock(return_value={"age": 50})),
        patch.object(RiskRecommendationService, "_enforce_throttle", AsyncMock(return_value=None)),
        patch(f"{_MOD}.run_risk_recommendation", AsyncMock(side_effect=OperationalError("db down"))),
        pytest.raises(HTTPException) as exc_info,
    ):
        await RiskRecommendationService().recommend(user_id=_USER_ID)
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


async def test_save_cache_failure_is_best_effort() -> None:
    """이력 저장(_save_cache) 실패해도 유효 결과 반환 + Redis set 은 계속 호출돼 재호출 루프 차단."""
    set_reco = AsyncMock()
    set_snapshot = AsyncMock()
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=None)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value=None)),
        patch(f"{_MOD}.compute_feature_snapshot", AsyncMock(return_value={"age": 50})),
        patch.object(RiskRecommendationService, "_enforce_throttle", AsyncMock(return_value=None)),
        patch(f"{_MOD}.run_risk_recommendation", AsyncMock(return_value=_valid_result())),
        patch.object(RiskRecommendationService, "_save_cache", AsyncMock(side_effect=OperationalError("write fail"))),
        patch(f"{_CACHE}.set_reco", set_reco),
        patch(f"{_CACHE}.set_snapshot", set_snapshot),
    ):
        resp = await RiskRecommendationService().recommend(user_id=_USER_ID)

    assert resp.answer == "권고 본문"
    # set_reco 는 결과 블록(_save_cache 직후)에서만 호출 — 저장 실패에도 실행됐다는 건
    # 다음 요청이 캐시로 단락돼 LLM 재호출 루프가 끊긴다는 보장.
    set_reco.assert_awaited_once()
    set_snapshot.assert_awaited()  # snapshot 캐싱 + 결과 저장 두 경로에서 호출
