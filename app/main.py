from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.databases import initialize_tortoise
from app.core.responses import ORJSONResponse

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
_media_root = Path(config.MEDIA_ROOT)
_media_root.mkdir(parents=True, exist_ok=True)
app.mount(config.MEDIA_URL_PREFIX, StaticFiles(directory=str(_media_root)), name="media")

app.include_router(v1_routers)
