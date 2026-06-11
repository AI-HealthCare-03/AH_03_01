"""위험도 예측 비동기 워커 경로 테스트.

- 워커 `_process_message`: PENDING row → v2 입력 복원 → 추론 → SUCCESS/FAILED row 갱신.
- 그래프 `_ml_inference_async`: PENDING row + 큐 push(모킹) → 결과 폴링 / 타임아웃 룰 폴백.

LLM·실모델 의존 없이 내부 함수를 직접 호출한다(추론은 monkeypatch/룰 폴백).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from tortoise.contrib.test import TestCase

import ai_worker.risk_inference.worker as worker
import app.graphs.risk_recommendation_graph as graph
from app.core import config
from app.models.health import DiseaseType, RiskLevel
from app.models.ml_inference import MLInferenceKind, MLInferenceRequest, MLInferenceStatus
from app.models.users import User
from app.services.ml.risk_predictor import PredictionOutput, RiskFactor
from app.tests.health_apis.helpers import make_client, signup_and_login

# 그래프 snapshot / 워커 input_features 와 동일한 v2 28필드(+age/gender/disease_type) 예시.
_SNAPSHOT = {
    "disease_type": "DIABETES",
    "age": 50,
    "gender": "MALE",
    "height_cm": 170.0,
    "weight_kg": 80.0,
    "waist_cm": 92.0,
    "systolic_bp": 135.0,
    "diastolic_bp": 88.0,
    "fasting_blood_sugar": 110.0,
    "sleep_weekday": 6.5,
    "sleep_weekend": 7.5,
    "moderate_exercise_hour": 0.5,
    "smoking_risk": 1.0,
    "mid_act_day": 3,
    "walk_day": 5,
    "water_count": 6,
    "family_dm": 1,
    "family_hp": 0,
    "family_hl": -1,
    "current_smoker": 1,
    "alcohol_freq_y": 5,
    "alcohol_cup": 2,
    "fruit_freq": 5,
    "veg_freq_1": 2,
    "out_meal_freq": 3,
    "breakfast_freq": 1,
    "is_menopause": -1,
    "ocp_total_months": 0,
    "anemia": 0,
}


async def _make_user(email: str, phone: str):
    """signup 으로 유저 1명 생성 후 ORM 으로 조회해 UUID 반환."""
    async with make_client() as client:
        await signup_and_login(client, email=email, phone_number=phone)
    user = await User.filter(email=email).first()
    assert user is not None
    return user.id


def _fake_output(dt: DiseaseType) -> PredictionOutput:
    return PredictionOutput(
        disease_type=dt,
        risk_score=Decimal("72"),
        risk_level=RiskLevel.RISK,
        contributing_factors=[RiskFactor(factor="systolic_bp", weight=0.5, description="혈압 높음")],
        model_version="ml-test",
    )


class TestPayloadFromInput:
    def test_v2_roundtrip(self):
        """워커 입력 복원이 snapshot 28필드를 정확히 복원하는지(필드명 정합)."""
        p = worker._payload_from_input(DiseaseType.DIABETES, _SNAPSHOT)
        assert p.disease_type == DiseaseType.DIABETES
        assert p.systolic_bp is not None and float(p.systolic_bp) == 135.0
        assert p.family_hl == -1 and p.current_smoker == 1 and p.alcohol_freq_y == 5
        assert p.water_count == 6 and p.is_menopause == -1 and p.anemia == 0
        # snapshot 키가 PredictionInput 필드로 모두 복원되는지(누락/오타 검출)
        recon = p.snapshot()
        assert all(k in recon for k in _SNAPSHOT)


class TestWorkerProcessMessage(TestCase):
    async def test_success_updates_row(self):
        uid = await _make_user("worker_ok@example.com", "01055550001")
        req = await MLInferenceRequest.create(
            user_id=uid,
            kind=MLInferenceKind.RISK_PREDICTION,
            status=MLInferenceStatus.PENDING,
            input_features=_SNAPSHOT,
        )

        async def fake_inf(payload):
            return _fake_output(payload.disease_type)

        with patch.object(worker, "_run_inference", fake_inf):
            await worker._process_message({"request_id": req.id})

        row = await MLInferenceRequest.get(id=req.id)
        assert row.status == MLInferenceStatus.SUCCESS
        assert row.prediction_result is not None
        assert row.prediction_result["disease_type"] == "DIABETES"
        assert row.prediction_result["risk_score"] == 72.0
        assert row.prediction_result["risk_level"] == RiskLevel.RISK.value
        assert row.model_version == "ml-test"
        assert row.duration_ms is not None

    async def test_failure_marks_failed(self):
        uid = await _make_user("worker_fail@example.com", "01055550002")
        req = await MLInferenceRequest.create(
            user_id=uid,
            kind=MLInferenceKind.RISK_PREDICTION,
            status=MLInferenceStatus.PENDING,
            input_features=_SNAPSHOT,
        )

        async def boom(payload):
            raise RuntimeError("model broke")

        with patch.object(worker, "_run_inference", boom):
            await worker._process_message({"request_id": req.id})

        row = await MLInferenceRequest.get(id=req.id)
        assert row.status == MLInferenceStatus.FAILED
        assert "RuntimeError" in (row.error_message or "")


class TestGraphAsyncDispatch(TestCase):
    async def test_async_success_polls_worker_result(self):
        uid = await _make_user("graph_async_ok@example.com", "01055550003")

        # 워커 즉시 처리 시뮬레이트: enqueue 시 해당 row 를 SUCCESS 로 채운다.
        async def fake_enqueue(payload):
            row = await MLInferenceRequest.get(id=payload["request_id"])
            dt = row.input_features["disease_type"]
            row.status = MLInferenceStatus.SUCCESS
            row.prediction_result = {
                "disease_type": dt,
                "risk_score": 55.0,
                "risk_level": RiskLevel.CAUTION.value,
                "contributing_factors": [],
                "model_version": "ml-test",
            }
            await row.save()

        state = {"user_id": uid, "thread_id": "t-ok", "feature_snapshot": _SNAPSHOT}
        with (
            patch.object(config, "RISK_INFERENCE_ASYNC", True),
            patch.object(graph, "enqueue_risk_inference", fake_enqueue),
        ):
            out = await graph._ml_inference_async(state)

        assert len(out["predictions"]) == 3
        assert len(out["ml_request_ids"]) == 3
        assert all(p["risk_score"] == 55.0 for p in out["predictions"])
        # 3 질환 row 모두 SUCCESS 로 채워졌는지
        rows = await MLInferenceRequest.filter(id__in=out["ml_request_ids"])
        assert all(r.status == MLInferenceStatus.SUCCESS for r in rows)

    async def test_async_timeout_falls_back_to_rule(self):
        uid = await _make_user("graph_async_to@example.com", "01055550004")

        async def noop_enqueue(payload):
            # 워커 없음 → row 는 PENDING 으로 남고 폴링 타임아웃 → 룰 폴백
            return None

        state = {"user_id": uid, "thread_id": "t-to", "feature_snapshot": _SNAPSHOT}
        with (
            patch.object(config, "RISK_INFERENCE_ASYNC", True),
            patch.object(config, "RISK_INFERENCE_POLL_TIMEOUT", 0.05),
            patch.object(config, "RISK_INFERENCE_POLL_INTERVAL", 0.01),
            patch.object(graph, "enqueue_risk_inference", noop_enqueue),
        ):
            out = await graph._ml_inference_async(state)

        # 폴백이라도 3개 예측 반환, 단 워커 성공 row 는 없으므로 request_ids 비어있음
        assert len(out["predictions"]) == 3
        assert out["ml_request_ids"] == []
        assert all("risk_score" in p and "risk_level" in p for p in out["predictions"])
