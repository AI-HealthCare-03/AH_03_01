"""Redis 기반 단일 큐 인터페이스.

publisher (app) 와 consumer (ai_worker) 가 공유. JSON 직렬화한 작업 메시지를
`LPUSH queue:image-verification <json>` 로 push, consumer 는 `BRPOP` 으로 pop.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis_async

from app.core import config

_async_client: redis_async.Redis | None = None


def _get_async_client() -> redis_async.Redis:
    global _async_client
    if _async_client is None:
        _async_client = redis_async.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
    return _async_client


async def enqueue_image_verification(payload: dict[str, Any]) -> None:
    """app 측에서 호출. payload 예: {"job_id": 1, "verification_id": 2, "file_id": 3, "category": "WATER"}"""
    client = _get_async_client()
    # redis-py async client 의 lpush 는 Awaitable 반환. mypy union 추론 회피용 cast.
    await client.lpush(config.IMAGE_VERIFY_QUEUE, json.dumps(payload, ensure_ascii=False))  # type: ignore[misc]
