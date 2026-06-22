import logging
from typing import Any

from app.core import config

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
    "app.models.community",
    "app.models.support",
    "app.models.notifications",
    "app.models.risk_recommendation_result",
    "app.models.medication_reminder",
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


def init_tortoise_models() -> None:
    """모델 간 관계를 등록한다(DB 연결 불필요, import 시점에 안전).

    실제 DB 연결/풀 초기화는 main.lifespan 의 RegisterTortoise 가 담당한다.
    과거 register_tortoise 는 on_startup 이벤트 핸들러로 DB 를 초기화했는데, 커스텀 lifespan 의
    pre-yield 코드(스케줄러·BM25 warmup)가 그보다 먼저 실행돼 'DB 미연결 상태에서 쿼리' 문제가
    있었다. lifespan 안에서 RegisterTortoise 로 연결을 먼저 연 뒤 스케줄러/warmup 을 돌려 해소한다.
    ai_worker(ai 그룹만 설치) 는 자체적으로 Tortoise.init 을 호출한다.
    """
    from tortoise import Tortoise

    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
