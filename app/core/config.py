import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic import model_validator
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

    @model_validator(mode="after")
    def _guard_prod_db_host(self) -> "Config":
        # PROD 에서 DB_HOST 가 RDS 엔드포인트로 주입되지 않으면(=.env 누락/오타) 부팅 거부.
        # default localhost 로 조용히 폴백해 엉뚱한 DB 에 운영 트래픽이 쓰이는 사고 방지.
        if self.ENV == Env.PROD and self.DB_HOST in ("", "localhost", "127.0.0.1"):
            raise ValueError("PROD 환경에서 DB_HOST 가 RDS 엔드포인트로 설정되지 않았습니다.")
        return self

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # 미디어/파일 업로드
    MEDIA_ROOT: str = "/app/media"
    MEDIA_URL_PREFIX: str = "/media"
    # signed-URL 만료(초). 읽을 때마다 새 서명을 발급하므로, 응답을 받은 뒤
    # 이 시간 안에 표시하면 된다(이미지 캐시 만료 방지 위해 넉넉히 1일).
    MEDIA_URL_TTL: int = 24 * 60 * 60
    UPLOAD_MAX_BYTES: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_IMAGE_MIME: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

    # Redis / 큐
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    IMAGE_VERIFY_QUEUE: str = "queue:image-verification"
    # 위험도 예측 ML 추론 큐 (risk-worker BRPOP consumer)
    RISK_INFERENCE_QUEUE: str = "queue:ml-inference"
    # ml_inference 노드 dispatch 모드: True=Redis 큐+워커 비동기, False=P1 동기(인라인 RiskPredictor)
    RISK_INFERENCE_ASYNC: bool = False
    # async 모드에서 노드가 결과 row 를 폴링하는 간격/최대 대기(초). 타임아웃 시 인라인 룰 폴백.
    RISK_INFERENCE_POLL_INTERVAL: float = 0.2
    RISK_INFERENCE_POLL_TIMEOUT: float = 15.0
    # True 면 ML 모델 로드/추론 실패 시 룰로 조용히 폴백하지 않고 MLUnavailableError 를 던진다.
    # (prod 에서 켜면 예측 결과가 항상 진짜 ML 임을 보장 — 모델 장애가 룰로 가려지지 않음.)
    # 로컬/테스트 기본 False(룰 폴백으로 graceful degrade 유지).
    RISK_REQUIRE_ML: bool = False

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

    # 이메일 발송 (SMTP) — 본인 인증 메일 등.
    # SMTP_HOST/SMTP_USER 가 비어 있으면 실발송 대신 인증 링크를 콘솔(로그)에 출력한다.
    # 포트 465=implicit TLS(권장, RFC 8314), 587=STARTTLS. send_email 이 포트로 자동 분기.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TIMEOUT: float = 10.0
    # 인증 링크에 사용할 프론트엔드 베이스 URL (예: http://localhost:3000)
    FRONTEND_BASE_URL: str = "http://localhost:3000"
