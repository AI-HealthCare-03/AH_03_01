"""ai_worker 위험도 예측 워커 (3단계 비동기 전환: 큐 + 워커 + 노드 폴링).

설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 3단계.

본 워커는 `_run_inference()` 에서 `RiskPredictor`(학습된 ML 모델 + 룰 폴백)를 호출해
실제 추론을 수행한다. SigLIP 워커(`ai_worker/main.py`)와 분리된 전용 컨테이너
(docker-compose `risk-worker`, `python -m ai_worker.risk_inference.worker`)로 실행된다.

⚠️ 가동 조건: 그래프 `RiskRecommendationGraph.ml_inference` 노드가 `RISK_INFERENCE_ASYNC`
플래그에 따라 Redis 큐로 dispatch 할 때만 메시지가 들어온다. 플래그 OFF(기본)에서는
노드가 P1 동기(`RiskPredictor` 직접 호출)로 동작하고 본 워커는 빈 큐를 idle 폴링한다.
(그래프 dispatch·플래그 배선 = 후속 PR. 4단계 interrupt/resume + SSE 는 별도.)

큐 메시지 포맷(JSON):
{
  "request_id": <int>,    # ml_inference_requests.id
  "user_id":    <uuid>,
  "thread_id":  <str | null>,
  "kind":       "RISK_PREDICTION",
  "input_features": { ... }    # PredictionInput.snapshot()
}

처리 흐름:
    BRPOP queue:ml-inference
      → ml_inference_requests.status = RUNNING, started_at=now()
      → _run_inference() — ML 모델(또는 룰 폴백) 호출
      → status = SUCCESS, prediction_result 채움, duration_ms 계산
      → (옵션) Redis pub/sub publish 로 그래프에 완료 알림 (4단계 SSE 와 결합)

챌린지 인증 워커(`ai_worker/main.py`) 와 동일 패턴 — 같은 BRPOP + DB job 테이블
구조를 그대로 따른다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from tortoise import Tortoise

from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.models.health import DiseaseType
from app.models.ml_inference import (
    MLInferenceRequest,
    MLInferenceStatus,
)
from app.services.ml.risk_predictor import (
    PredictionInput,
    PredictionOutput,
    RiskPredictor,
)

logger = logging.getLogger("ai_worker.risk_inference")

# Redis 큐 키 — config 단일 출처(.env 의 RISK_INFERENCE_QUEUE 로 오버라이드 가능).
QUEUE_KEY = config.RISK_INFERENCE_QUEUE
# BRPOP 타임아웃(초). 종료 신호를 짧은 간격으로 확인.
BRPOP_TIMEOUT = 5

_should_exit = False


def _install_signal_handlers() -> None:
    def _handler(signum: int, _frame: Any) -> None:
        global _should_exit
        logger.info("signal %s received, shutting down", signum)
        _should_exit = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


@asynccontextmanager
async def _tortoise_session():
    """ai_worker 는 마이그레이션 관리를 하지 않으므로 aerich.models 제외 후 init."""
    worker_config = {
        **TORTOISE_ORM,
        "apps": {
            "models": {
                "models": [m for m in TORTOISE_ORM["apps"]["models"]["models"] if m != "aerich.models"],
            },
        },
    }
    await Tortoise.init(config=worker_config)
    try:
        yield
    finally:
        await Tortoise.close_connections()


def _to_dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


def _payload_from_input(disease_type: DiseaseType, snap: dict[str, Any]) -> PredictionInput:
    """input_features(PredictionInput.snapshot()) dict 를 v2 PredictionInput 으로 복원.

    키 셋은 그래프 `_build_prediction_input` / `PredictionInput.snapshot()` 과 1:1 미러.
    Decimal 수치형은 _to_dec, 설문 코드형(int, 0·-1 유효)은 그대로 전달.
    """
    return PredictionInput(
        disease_type=disease_type,
        age=snap.get("age"),
        gender=snap.get("gender"),
        height_cm=_to_dec(snap.get("height_cm")),
        weight_kg=_to_dec(snap.get("weight_kg")),
        waist_cm=_to_dec(snap.get("waist_cm")),
        systolic_bp=_to_dec(snap.get("systolic_bp")),
        diastolic_bp=_to_dec(snap.get("diastolic_bp")),
        fasting_blood_sugar=_to_dec(snap.get("fasting_blood_sugar")),
        sleep_weekday=_to_dec(snap.get("sleep_weekday")),
        sleep_weekend=_to_dec(snap.get("sleep_weekend")),
        moderate_exercise_hour=_to_dec(snap.get("moderate_exercise_hour")),
        smoking_risk=_to_dec(snap.get("smoking_risk")),
        mid_act_day=snap.get("mid_act_day"),
        walk_day=snap.get("walk_day"),
        water_count=snap.get("water_count"),
        family_dm=snap.get("family_dm"),
        family_hp=snap.get("family_hp"),
        family_hl=snap.get("family_hl"),
        current_smoker=snap.get("current_smoker"),
        alcohol_freq_y=snap.get("alcohol_freq_y"),
        alcohol_cup=snap.get("alcohol_cup"),
        fruit_freq=snap.get("fruit_freq"),
        veg_freq_1=snap.get("veg_freq_1"),
        out_meal_freq=snap.get("out_meal_freq"),
        breakfast_freq=snap.get("breakfast_freq"),
        is_menopause=snap.get("is_menopause"),
        ocp_total_months=snap.get("ocp_total_months"),
        anemia=snap.get("anemia"),
    )


# 모듈 레벨 — 모델 아티팩트를 최초 추론 시 1회 로드해 워커 수명 동안 warm 유지.
_predictor = RiskPredictor()


async def _run_inference(payload: PredictionInput) -> PredictionOutput:
    """실제 ML 추론 — RiskPredictor(학습된 모델 + 룰 폴백).

    RiskPredictor 가 내부적으로 ML 모델 호출을 시도하고, 로드/추론 실패 시 룰 기반으로
    자동 폴백한다. CPU-bound 추론이지만 본 워커 전용 프로세스라 이벤트루프 블로킹 무해.
    """
    return await _predictor.predict(payload)


async def _process_message(message: dict[str, Any]) -> None:
    """큐에서 받은 메시지 1건 처리.

    request_id 로 ml_inference_requests row 를 조회 → status=RUNNING → 추론 →
    결과 row 업데이트. 실패 시 status=FAILED + error_message 기록.
    """
    request_id = int(message.get("request_id", 0))
    if not request_id:
        logger.warning("malformed message — request_id 누락: %s", message)
        return

    request = await MLInferenceRequest.filter(id=request_id).first()
    if request is None:
        logger.warning("ml_inference_requests row 없음: id=%d", request_id)
        return

    request.status = MLInferenceStatus.RUNNING
    request.started_at = datetime.now(tz=UTC)
    await request.save()

    t0 = datetime.now(tz=UTC)
    try:
        input_features = request.input_features or {}
        disease_type_str = input_features.get("disease_type", "DIABETES")
        try:
            disease_type = DiseaseType(disease_type_str)
        except ValueError:
            disease_type = DiseaseType.DIABETES
        payload = _payload_from_input(disease_type, input_features)
        output = await _run_inference(payload)
        request.status = MLInferenceStatus.SUCCESS
        request.model_version = output.model_version
        request.prediction_result = {
            "disease_type": output.disease_type.value,
            "risk_score": float(output.risk_score),
            "risk_level": output.risk_level.value,
            "contributing_factors": [f.to_dict() for f in output.contributing_factors],
            "model_version": output.model_version,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("ml_inference 처리 실패: request_id=%d", request_id)
        request.status = MLInferenceStatus.FAILED
        request.error_message = f"{type(e).__name__}: {str(e)[:200]}"
    finally:
        request.completed_at = datetime.now(tz=UTC)
        request.duration_ms = int((request.completed_at - t0).total_seconds() * 1000)
        await request.save()


async def _main_loop() -> None:
    """BRPOP 폴링 루프 — 챌린지 인증 워커와 동일 구조.

    ⚠️ 현재 ai_worker/main.py 에 등록되지 않아 가동 안 됨. ML 학습 완료 시 활성화.
    """
    import redis.asyncio as redis  # lazy import

    client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
    logger.info("risk_inference worker started — queue=%s", QUEUE_KEY)
    try:
        while not _should_exit:
            try:
                raw = await client.brpop([QUEUE_KEY], timeout=BRPOP_TIMEOUT)  # type: ignore[misc]
            except Exception as e:  # noqa: BLE001
                logger.warning("BRPOP 실패, 재시도: %s", type(e).__name__)
                await asyncio.sleep(1)
                continue
            if raw is None:
                continue  # timeout — 종료 신호 체크용
            _, payload = raw
            try:
                message = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning("malformed JSON: %r", payload[:200])
                continue
            await _process_message(message)
    finally:
        await client.aclose()
        logger.info("risk_inference worker stopped")


async def main() -> None:
    """엔트리포인트 — `python -m ai_worker.risk_inference.worker` 또는
    ai_worker/main.py 의 asyncio.gather 에 추가하여 활성화.
    """
    _install_signal_handlers()
    async with _tortoise_session():
        await _main_loop()


if __name__ == "__main__":
    asyncio.run(main())
