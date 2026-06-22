FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 1. uv 설치 (공식 이미지에서 복사해오는 가장 깔끔한 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. pyproject.toml에 명시된 의존성 패키지 중에서 'app' 그룹만 설치합니다.
RUN uv sync --group app --no-dev --frozen

# 3-1. 월간 리포트 PDF 렌더용 chromium + 시스템 의존성 + 한글 폰트(fonts-nanum).
#      playwright install --with-deps 가 chromium 실행에 필요한 OS 라이브러리를 함께 설치한다.
#      한글 폰트가 없으면 PDF 의 한글이 깨지므로(tofu) fonts-nanum 을 명시 설치.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-nanum fonts-noto-cjk \
    && uv run --no-sync playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# 4. ML 모델 아티팩트(예측 모델 번들)를 이미지에 포함합니다.
#    models/ 는 git 미추적이라 빌드 머신의 models/ 디렉터리가 그대로 구워집니다.
#    MODEL_ARTIFACT_DIR=/app/models/rb3_... 와 경로 일치. 모델 재튜닝 시 models/ 교체 후 재빌드.
#    (app 코드보다 변경이 드물어 캐시 효율을 위해 COPY ./app 보다 먼저 둡니다.)
COPY ./models ./models

# 5. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
COPY ./app ./app

# 5. 해당 이미지를 활용하여 도커컨테이너 실행시 실행되는 명령어입니다.
# FastAPI를 uvicorn을 활용하여 비동기 환경으로 서버를 실행합니다.
# --no-sync 옵션은 uv run시 uv.lock파일과 환경에 설치된 패키지들을 비교하여 없는 패키지를 설치하기 때문에
# 불필요한 의존성을 설치하지 않기 위해 사용합니다.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
