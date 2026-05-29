import logging
from typing import TYPE_CHECKING, Any

from app.core import config

if TYPE_CHECKING:
    from fastapi import FastAPI

_logger = logging.getLogger(__name__)
_pgvector_codec_warned = False  # 부팅당 1회만 경고 (풀의 init 이 연결마다 호출되므로 중복 방지)

TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.users",
    "app.models.health",
    "app.models.rag",
    "app.models.challenge",
    "app.models.pet",
    "app.models.chatbot",
    "app.models.files",
    "app.models.experience",
    "app.models.ml_inference",
]


async def _register_pgvector_codec(connection: Any) -> None:
    """asyncpg 새 연결마다 pgvector 코덱을 등록한다.

    `asyncpg.create_pool(init=...)` 콜백으로 사용 (아래 TORTOISE_ORM credentials.init 참조).
    pgvector 확장이 없는 환경에서도 부팅이 깨지지 않도록 예외는 흡수하되,
    silent 실패로 RAG 가 사일런트로 죽는 걸 방지하기 위해 부팅당 1회 경고를 남긴다.
    """
    global _pgvector_codec_warned
    try:
        from pgvector.asyncpg import register_vector  # type: ignore[import-untyped]

        raw_conn = getattr(connection, "_connection", None) or connection
        await register_vector(raw_conn)
    except Exception as e:  # noqa: BLE001 — DB without pgvector도 부팅은 가능해야 함
        if not _pgvector_codec_warned:
            _pgvector_codec_warned = True
            _logger.warning(
                "pgvector 코덱 등록 실패 — RAG 검색이 비활성화될 수 있음 (%s: %s)",
                type(e).__name__,
                str(e)[:200],
            )


TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "user": config.DB_USER,
                "password": config.DB_PASSWORD,
                "database": config.DB_NAME,
                "minsize": 1,
                "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
                # asyncpg.create_pool(init=...) 로 전달돼 신규 연결마다 pgvector 코덱 등록.
                # (Tortoise 의 잉여 credentials 키는 self.extra 를 통해 create_pool 에 전개됨)
                "init": _register_pgvector_codec,
            },
        },
    },
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: "FastAPI") -> None:
    """FastAPI 앱 시작 시 Tortoise 초기화 + 자동 lifecycle 연결.

    fastapi/register_tortoise 는 ai_worker (ai 그룹만 설치) 에서는 불필요하므로
    함수 본문에서 lazy import 한다. ai_worker 는 자체적으로 Tortoise.init 을 호출.
    """
    from tortoise import Tortoise
    from tortoise.contrib.fastapi import register_tortoise

    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)
