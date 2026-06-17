import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.apis.media import media_router
from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.databases import initialize_tortoise
from app.core.limiter import limiter
from app.core.responses import ORJSONResponse
from app.core.scheduler import start_scheduler, stop_scheduler

_logger = logging.getLogger(__name__)


async def _warmup_bm25_index() -> None:
    """부팅 시 BM25 인덱스를 미리 빌드해 첫 사용자 요청의 cold start 비용을 제거한다.

    실패 시 첫 retrieve 시점의 lazy build 가 다시 시도되므로 부팅은 계속 진행한다.
    OpenAI API 호출은 없고 RAGDocument DB 조회 + Kiwi 형태소 분석만 수행.
    """
    try:
        from app.services.ml.retrieval import _get_bm25_index

        index = await _get_bm25_index()
        _logger.info("BM25 인덱스 warmup 완료 (corpus=%d)", len(index.chunk_ids))
    except Exception as e:  # noqa: BLE001 — RAGDocument 부재/Kiwi 누락 등 어떤 실패도 부팅 차단 X
        _logger.warning("BM25 warmup 실패, lazy build 로 폴백: %s", type(e).__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    start_scheduler()
    # Tortoise 초기화 완료 후 BM25 warmup 실행 (lifespan 내부에서만 DB 접근 가능)
    await _warmup_bm25_index()
    yield
    stop_scheduler()


app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)


@app.get("/api/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """경량 헬스체크 — DB/외부의존 없이 즉시 200. 배포 readiness 체크·모니터링용."""
    return {"status": "ok"}


# 레이트리밋(slowapi): 라우터의 @limiter.limit 데코레이터가 app.state.limiter 를 참조.
app.state.limiter = limiter
# slowapi 핸들러 시그니처가 Starlette 의 (Request, Exception) 와 정확히 일치하지 않음(알려진 타입 이슈).
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


async def _redis_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """Redis 장애 시 미처리 500 대신 명확한 503 으로 응답한다(인증 플래그 게이트 등은 fail-closed 유지)."""
    _logger.error("Redis 오류로 요청 처리 실패: %s", type(exc).__name__)
    return ORJSONResponse(
        content={"detail": "일시적인 오류로 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


app.add_exception_handler(RedisError, _redis_error_handler)  # type: ignore[arg-type]

# 로컬 프론트엔드(Next.js dev) 와 운영 도메인에서 호출 허용.
_cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000", config.FRONTEND_BASE_URL]
if config.EXTRA_CORS_ORIGIN:
    _cors_origins.append(config.EXTRA_CORS_ORIGIN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

initialize_tortoise(app)

# /media 서빙: 무인증 StaticFiles 대신 signed-URL 검증 라우트(app/apis/media.py).
# 업로드 파일은 PHI(예: 챌린지 인증 사진)를 포함할 수 있어 서명·만료 게이트를 둔다.
app.include_router(media_router)

app.include_router(v1_routers)
