"""위험도 권고 2-tier 캐시 — Redis(단기) + DB(장기 append-only).

세션 중 건강정보 수정이 드물다는 전제로, 반복 위험도 요청 시 DB 쿼리·그래프
호출을 0회로 만들기 위한 Redis 단기 캐시 레이어. 진실 원본은 DB(append-only 이력),
Redis 는 가속 캐시이므로 GET/SET 실패는 best-effort 로 흡수하고 DB/그래프 경로로 폴백한다.

키 (둘 다 TTL 24h):
- ``risk:snapshot:{user_id}`` — 현재 feature_snapshot JSON (건강정보 단기 캐싱).
- ``risk:reco:{user_id}``     — 직전 성공 응답 + 그 때 쓴 snapshot/model_version 동봉 JSON.

건강정보(프로필/일별 레코드)가 바뀌면 두 키를 함께 무효화해야 정합성이 유지된다
(:func:`invalidate_risk_cache`). Redis 클라이언트 패턴은 ``email_verification`` 과 동일.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis_async

from app.core import config

logger = logging.getLogger(__name__)

# 건강정보 수정 빈도가 낮아 24h 보관해도 stale 위험이 작고, 무효화 훅으로 즉시 정리된다.
_TTL_SEC = 24 * 60 * 60
_SNAPSHOT_KEY = "risk:snapshot:{user_id}"
_RECO_KEY = "risk:reco:{user_id}"

_redis: redis_async.Redis | None = None


def _client() -> redis_async.Redis:
    global _redis
    if _redis is None:
        _redis = redis_async.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
    return _redis


async def get_snapshot(user_id: Any) -> dict[str, Any] | None:
    """Redis 에 캐싱된 현재 feature_snapshot. 미스/장애 시 None (best-effort)."""
    try:
        raw = await _client().get(_SNAPSHOT_KEY.format(user_id=user_id))
    except Exception as exc:  # noqa: BLE001 — Redis 장애는 흡수하고 DB 경로로 폴백
        logger.warning("risk cache get_snapshot 실패 (user=%s): %s", user_id, exc)
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def set_snapshot(user_id: Any, snapshot: dict[str, Any]) -> None:
    """현재 feature_snapshot 을 캐싱 (TTL 24h). best-effort."""
    try:
        await _client().set(_SNAPSHOT_KEY.format(user_id=user_id), json.dumps(snapshot), ex=_TTL_SEC)
    except Exception as exc:  # noqa: BLE001
        logger.warning("risk cache set_snapshot 실패 (user=%s): %s", user_id, exc)


async def get_reco(user_id: Any) -> dict[str, Any] | None:
    """직전 성공 응답 + 동봉 snapshot/model_version. 미스/장애 시 None (best-effort).

    반환 dict 구조: ``{"snapshot": {...}, "model_version": "...", "response": {...}}``.
    """
    try:
        raw = await _client().get(_RECO_KEY.format(user_id=user_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("risk cache get_reco 실패 (user=%s): %s", user_id, exc)
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def set_reco(
    user_id: Any,
    *,
    snapshot: dict[str, Any],
    model_version: str,
    response: dict[str, Any],
) -> None:
    """직전 성공 응답을 그 때 쓴 snapshot/model_version 과 함께 캐싱 (TTL 24h). best-effort."""
    payload = {"snapshot": snapshot, "model_version": model_version, "response": response}
    try:
        await _client().set(_RECO_KEY.format(user_id=user_id), json.dumps(payload), ex=_TTL_SEC)
    except Exception as exc:  # noqa: BLE001
        logger.warning("risk cache set_reco 실패 (user=%s): %s", user_id, exc)


async def invalidate_risk_cache(user_id: Any) -> None:
    """건강정보 쓰기 시 두 키(snapshot/reco)를 DEL — stale 캐시 정합성 보호. best-effort.

    UserHealthInfo 갱신(건강 폼 저장) 과 HealthRecord 생성(일별 레코드) 경로에서만 호출한다.
    이 둘이 feature_snapshot 입력(레코드 폴백 포함)에 영향을 주는 유일한 쓰기 경로다.
    """
    try:
        await _client().delete(
            _SNAPSHOT_KEY.format(user_id=user_id),
            _RECO_KEY.format(user_id=user_id),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("risk cache invalidate 실패 (user=%s): %s", user_id, exc)
