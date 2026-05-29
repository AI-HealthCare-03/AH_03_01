import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.databases import initialize_tortoise
from app.core.responses import ORJSONResponse

_logger = logging.getLogger(__name__)

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)

# 로컬 프론트엔드(Next.js dev) 와 운영 도메인에서 호출 허용.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

initialize_tortoise(app)

# /media 정적 파일 서빙. 업로드된 이미지/리소스에 접근 가능.
# 컨테이너 환경 기본값 /app/media 는 CI / 로컬에서 권한 거부될 수 있으므로
# mkdir 실패 시 ./.media 로 폴백한다.
try:
    _media_root = Path(config.MEDIA_ROOT)
    _media_root.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    _media_root = Path.cwd() / ".media"
    _media_root.mkdir(parents=True, exist_ok=True)
app.mount(config.MEDIA_URL_PREFIX, StaticFiles(directory=str(_media_root)), name="media")

app.include_router(v1_routers)


async def _warmup_bm25_index() -> None:
    """부팅 시 BM25 인덱스를 미리 빌드해 첫 사용자 요청의 cold start 비용을 제거한다.

    실패 시 첫 retrieve 시점의 lazy build 가 다시 시도되므로 부팅은 계속 진행한다.
    OpenAI API 호출은 없고 RAGDocument DB 조회 + Kiwi 형태소 분석만 수행.
    """
    try:
        # circular import 방지를 위해 lazy import.
        from app.services.ml.retrieval import _get_bm25_index

        index = await _get_bm25_index()
        _logger.info("BM25 인덱스 warmup 완료 (corpus=%d)", len(index.chunk_ids))
    except Exception as e:  # noqa: BLE001 — RAGDocument 부재/Kiwi 누락 등 어떤 실패도 부팅 차단 X
        _logger.warning("BM25 warmup 실패, lazy build 로 폴백: %s", type(e).__name__)


# Tortoise 초기화 이후에 실행되도록 등록 순서 보존. register_tortoise 가 먼저 등록한
# startup 핸들러가 끝나야 RAGDocument 쿼리 가능.
app.add_event_handler("startup", _warmup_bm25_index)
