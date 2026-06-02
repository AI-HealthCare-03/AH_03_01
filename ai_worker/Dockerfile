FROM python:3.13-slim

WORKDIR /app

# 0. LightGBM 의존성 (libgomp — OpenMP 런타임)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 1. uv 설치 (공식 이미지에서 복사해오는 가장 깔끔한 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. pyproject.toml에 명시된 의존성 패키지 중에서 'app' 그룹만 설치합니다.
RUN uv sync --group ai --no-dev --frozen

# 4. 소스 코드 복사. ai_worker 가 Tortoise 모델을 직접 import 하므로 app/ 도 포함.
COPY ./ai_worker ./ai_worker
COPY ./app ./app

# Huggingface 모델 캐시 경로 (시작 시 SigLIP2 다운로드, 이후 캐시)
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface

# 5. SigLIP2 Redis 큐 consumer 실행 (BRPOP 무한 루프)
CMD ["uv", "run", "--no-sync", "python", "-m", "ai_worker.main"]
