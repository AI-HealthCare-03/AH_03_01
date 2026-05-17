from typing import TYPE_CHECKING, Any

from app.core import config

if TYPE_CHECKING:
    from fastapi import FastAPI

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
]

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


async def _register_pgvector_codec(connection: Any) -> None:
    """asyncpg 새 연결마다 pgvector 코덱을 등록한다."""
    try:
        from pgvector.asyncpg import register_vector  # type: ignore[import-untyped]

        raw_conn = getattr(connection, "_connection", None) or connection
        await register_vector(raw_conn)
    except (ImportError, Exception):  # noqa: BLE001 — DB without pgvector도 부팅은 가능해야 함
        pass


def initialize_tortoise(app: "FastAPI") -> None:
    """FastAPI 앱 시작 시 Tortoise 초기화 + 자동 lifecycle 연결.

    fastapi/register_tortoise 는 ai_worker (ai 그룹만 설치) 에서는 불필요하므로
    함수 본문에서 lazy import 한다. ai_worker 는 자체적으로 Tortoise.init 을 호출.
    """
    from tortoise import Tortoise
    from tortoise.contrib.fastapi import register_tortoise

    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)
