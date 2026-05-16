from typing import Any

from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.users",
    "app.models.health",
    "app.models.rag",
    "app.models.challenge",
    "app.models.pet",
    "app.models.chatbot",
    "app.models.files",
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


def initialize_tortoise(app: FastAPI) -> None:
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)
