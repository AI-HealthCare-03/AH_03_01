"""위험도 권고 SSE 스트리밍 단위 테스트.

- run_risk_recommendation_stream: astream_events 파싱(on_chain_start→stage, 루트 on_chain_end→result).
- RiskRecommendationService.recommend_stream: SSE 프레임 순서(meta→stage*→token*→done) / 캐시 히트 단락 /
  DB 장애·throttle 위반 → error 이벤트.

실 DB·LLM·그래프 실행 없이 의존성만 모킹한다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from tortoise.exceptions import OperationalError

from app.graphs.risk_recommendation_graph import (
    MODEL_VERSION,
    RiskRecommendationResult,
    run_risk_recommendation_stream,
)
from app.services.risk_recommendation import RiskRecommendationService

_MOD = "app.services.risk_recommendation"
_CACHE = "app.services.risk_recommendation_cache"
_GRAPH = "app.graphs.risk_recommendation_graph"
_USER_ID = "00000000-0000-0000-0000-000000000001"


def _valid_result() -> RiskRecommendationResult:
    return RiskRecommendationResult(
        answer="권고 본문입니다.",
        predictions=[],
        sources=[],
        has_required_data=True,
        is_fallback=False,
        feature_snapshot={"age": 50},
    )


def _parse_sse(frames: list[str]) -> list[tuple[str | None, Any]]:
    """SSE 프레임 문자열 리스트 → (event, data) 튜플 리스트."""
    out: list[tuple[str | None, Any]] = []
    for frame in frames:
        event: str | None = None
        data: Any = None
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:") :].strip())
        out.append((event, data))
    return out


async def _collect(agen: AsyncIterator[str]) -> list[tuple[str | None, Any]]:
    frames = [f async for f in agen]
    return _parse_sse(frames)


def _fake_graph_stream(events: list[tuple[str, Any]]):
    """run_risk_recommendation_stream 자리에 끼울 가짜 async 제너레이터 팩토리."""

    async def _gen(**_kwargs: Any) -> AsyncIterator[tuple[str, Any]]:
        for e in events:
            yield e

    return _gen


# ─────────────────────────────────────────────
# run_risk_recommendation_stream — astream_events 파싱
# ─────────────────────────────────────────────


class _FakeGraph:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    async def astream_events(self, _initial: Any, version: str) -> AsyncIterator[dict[str, Any]]:  # noqa: ARG002
        for e in self._events:
            yield e


async def test_graph_stream_emits_stages_then_result() -> None:
    """on_chain_start(STAGE_LABELS 노드)→stage, 루트 on_chain_end→result 매핑."""
    final_state = {
        "has_required_data": True,
        "final_answer": "최종 권고",
        "predictions": [],
        "sources": [],
        "recommended_tips": [],
        "recommended_diet": [],
        "is_fallback": False,
        "eval_revision_count": 0,
        "feature_snapshot": {"age": 50},
    }
    events: list[dict[str, Any]] = [
        {"event": "on_chain_start", "parent_ids": [], "run_id": "root", "name": "RiskRecommendationGraph"},
        {"event": "on_chain_start", "parent_ids": ["root"], "run_id": "n1", "name": "validate_input"},
        {"event": "on_chain_start", "parent_ids": ["root"], "run_id": "n2", "name": "preprocess"},  # 라벨X→스킵
        {"event": "on_chain_start", "parent_ids": ["root"], "run_id": "n3", "name": "ml_inference"},
        {"event": "on_chain_end", "run_id": "root", "data": {"output": final_state}},
    ]
    with patch(f"{_GRAPH}.RiskRecommendationGraph", return_value=_FakeGraph(events)):
        yielded = [item async for item in run_risk_recommendation_stream(user_id=_USER_ID)]

    stages = [name for kind, name in yielded if kind == "stage"]
    results = [payload for kind, payload in yielded if kind == "result"]
    assert stages == ["validate_input", "ml_inference"]  # preprocess(라벨 없음) 제외
    assert len(results) == 1
    assert isinstance(results[0], RiskRecommendationResult)
    assert results[0].answer == "최종 권고"


async def test_graph_stream_no_final_state_yields_fallback() -> None:
    """루트 on_chain_end 를 못 잡으면 fallback result 1개."""
    events: list[dict[str, Any]] = [
        {"event": "on_chain_start", "parent_ids": [], "run_id": "root", "name": "RiskRecommendationGraph"},
    ]
    with patch(f"{_GRAPH}.RiskRecommendationGraph", return_value=_FakeGraph(events)):
        yielded = [item async for item in run_risk_recommendation_stream(user_id=_USER_ID)]
    assert len(yielded) == 1
    kind, payload = yielded[0]
    assert kind == "result"
    assert payload.is_fallback is True


# ─────────────────────────────────────────────
# recommend_stream — SSE 프레임
# ─────────────────────────────────────────────


async def test_recommend_stream_cache_miss_meta_stage_done() -> None:
    """캐시 미스 → meta(cached=False) → stage* → token* → done."""
    stream_events = [("stage", "ml_inference"), ("stage", "retrieve"), ("result", _valid_result())]
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=None)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value=None)),
        patch(f"{_MOD}.compute_feature_snapshot", AsyncMock(return_value={"age": 50})),
        patch(f"{_CACHE}.set_snapshot", AsyncMock()),
        patch(f"{_CACHE}.set_reco", AsyncMock()),
        patch.object(RiskRecommendationService, "_enforce_throttle", AsyncMock(return_value=None)),
        patch.object(RiskRecommendationService, "_save_cache", AsyncMock(return_value=None)),
        patch(f"{_MOD}.run_risk_recommendation_stream", _fake_graph_stream(stream_events)),
    ):
        events = await _collect(RiskRecommendationService().recommend_stream(user_id=_USER_ID))

    names = [e for e, _ in events]
    assert names[0] == "meta"
    assert events[0][1] == {"cached": False}
    assert [d["node"] for e, d in events if e == "stage"] == ["ml_inference", "retrieve"]
    assert any(e == "token" for e, _ in events)
    assert names[-1] == "done"
    assert events[-1][1]["answer"] == "권고 본문입니다."


async def test_recommend_stream_cache_hit_short_circuits() -> None:
    """캐시 히트 → meta(cached=True) + done, stage 0개 (그래프 미실행)."""
    cached = {
        "model_version": MODEL_VERSION,
        "snapshot": {"age": 50},
        "response": {"answer": "캐시된 권고", "is_fallback": False},
    }
    stream_mock = MagicMock(side_effect=_fake_graph_stream([]))
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=cached)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value={"age": 50})),
        patch(f"{_MOD}.run_risk_recommendation_stream", stream_mock),
    ):
        events = await _collect(RiskRecommendationService().recommend_stream(user_id=_USER_ID))

    names = [e for e, _ in events]
    assert names == ["meta", "done"]
    assert events[0][1] == {"cached": True}
    assert events[1][1] == {"answer": "캐시된 권고", "is_fallback": False}
    stream_mock.assert_not_called()


async def test_recommend_stream_db_error_emits_error() -> None:
    """snapshot 산출 DB 장애 → error 이벤트 (503 대신)."""
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=None)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value=None)),
        patch(f"{_MOD}.compute_feature_snapshot", AsyncMock(side_effect=OperationalError("db down"))),
    ):
        events = await _collect(RiskRecommendationService().recommend_stream(user_id=_USER_ID))
    assert [e for e, _ in events] == ["error"]
    assert "건강 데이터" in events[0][1]["message"]


async def test_recommend_stream_throttle_emits_error() -> None:
    """throttle 위반(429) → error 이벤트(code=THROTTLED)."""
    throttle_exc = HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="쿨다운")
    with (
        patch(f"{_CACHE}.get_reco", AsyncMock(return_value=None)),
        patch(f"{_CACHE}.get_snapshot", AsyncMock(return_value=None)),
        patch(f"{_MOD}.compute_feature_snapshot", AsyncMock(return_value={"age": 50})),
        patch(f"{_CACHE}.set_snapshot", AsyncMock()),
        patch.object(RiskRecommendationService, "_enforce_throttle", AsyncMock(side_effect=throttle_exc)),
    ):
        events = await _collect(RiskRecommendationService().recommend_stream(user_id=_USER_ID))
    assert [e for e, _ in events] == ["error"]
    assert events[0][1].get("code") == "THROTTLED"
