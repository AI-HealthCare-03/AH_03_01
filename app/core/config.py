import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "pw1234"
    DB_NAME: str = "ai_health"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10

    COOKIE_DOMAIN: str = "localhost"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # 미디어/파일 업로드
    MEDIA_ROOT: str = "/app/media"
    MEDIA_URL_PREFIX: str = "/media"
    UPLOAD_MAX_BYTES: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_IMAGE_MIME: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

    # Redis / 큐
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    IMAGE_VERIFY_QUEUE: str = "queue:image-verification"

    # AI 모델
    SIGLIP_MODEL_NAME: str = "google/siglip2-base-patch16-224"
    SIGLIP_APPROVE_THRESHOLD: float = 0.20  # softmax 후 매칭 점수 임계

    # RAG / LLM (OpenAI) — 인덱싱·ChatRAGGraph 공용
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # 1536d
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    # 호출당 타임아웃(초). API 계약 §11 가이드(LLM 호출당 20초, 전체 ~45초)와 일치.
    # 그래프 노드가 fallback 으로 흡수하므로 SDK 재시도는 짧게(1).
    OPENAI_REQUEST_TIMEOUT: float = 20.0
    OPENAI_MAX_RETRIES: int = 1
