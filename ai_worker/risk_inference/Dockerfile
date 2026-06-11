# 위험도 예측 ML 추론 워커 (queue:ml-inference BRPOP consumer).
# 빌드 컨텍스트는 프로젝트 루트 (docker-compose 의 context: . 기준).
FROM python:3.13-slim

WORKDIR /app

# 1. uv 설치 (공식 이미지에서 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 메타 복사
COPY pyproject.toml uv.lock ./

# 3. app 그룹만 설치 — 모델 추론에 필요한 lightgbm/catboost/shap(+scikit-learn/numpy/
#    pandas/scipy transitive) + tortoise/asyncpg/redis 를 포함한다. SigLIP/torch(ai 그룹)는
#    이 워커가 쓰지 않으므로 제외해 이미지를 경량화한다. fastapi 와 동일 의존성 셋이라
#    학습된 모델 pickle 의 라이브러리 버전 호환도 보장된다.
RUN uv sync --group app --no-dev --frozen

# 4. 소스 코드 복사. 워커가 app/ 모듈(config·db·models·services.ml)을 import 하므로 함께 포함.
COPY ./ai_worker ./ai_worker
COPY ./app ./app

# 5. 위험도 예측 워커 실행 (queue:ml-inference BRPOP 무한 루프)
CMD ["uv", "run", "--no-sync", "python", "-m", "ai_worker.risk_inference.worker"]
