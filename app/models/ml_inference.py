"""ML 추론 요청 이력 — 위험도 예측 ML 호출 추적용.

설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 3단계.

본 테이블은 **3단계 비동기 워커 골격 선행** 으로 도입한다 (P1 동기 호출 단계에서도
request 등록·결과 저장을 통해 감사·디버깅·이력 추적 용도로 사용). 미래 ML 학습
완료 후엔 그래프의 `ml_inference` 노드가 직접 호출 → Redis 큐 dispatch + 워커
처리 + polling/interrupt 결과 수신 패턴으로 전환된다 (테이블·인덱스·status 흐름은
그대로 재사용).

흐름:
    1. 그래프 `ml_inference` 노드 진입 → row INSERT (status=PENDING)
    2. dispatch:
       - P1 (현재): 노드 안에서 RiskPredictor.predict() 동기 호출 → 결과 row 저장
         (status=SUCCESS, prediction_result/completed_at 채움)
       - 미래: Redis 큐 push → 워커 처리 → 결과 row 저장
    3. 다음 노드(persist_disease_risk → retrieve → generate ...)가 결과 활용

챌린지 인증 워커(`image_verification_jobs`) 패턴과 동일 구조 — 같은 BRPOP +
DB job 테이블 패턴을 위험도 예측 워커가 그대로 복제할 수 있도록 정렬한다.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class MLInferenceStatus(StrEnum):
    """위험도 추론 request 상태.

    PENDING: row 등록만, 아직 시작 안 됨 (워커 큐 대기 또는 노드 dispatch 직전).
    RUNNING: 추론 진행 중 (워커가 BRPOP 수령 직후).
    SUCCESS: 정상 완료. prediction_result 채워짐.
    FAILED:  예외/타임아웃. error_message 채워짐.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class MLInferenceKind(StrEnum):
    """ML 추론 종류 — 향후 다양한 ML 모델이 늘어날 때 구분 키."""

    RISK_PREDICTION = "RISK_PREDICTION"  # 위험도 예측 (현재 유일)


class MLInferenceRequest(models.Model):
    """ML 추론 요청·결과 단위 (감사·디버깅·이력).

    request 단위로 row 1개. 같은 사용자가 여러 번 위험도 예측을 요청해도 각각 신규
    row 누적 (DiseaseRisk 와 동일한 시계열 정책).
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="ml_inference_requests", on_delete=fields.CASCADE
    )
    # LangGraph 실행 추적용 thread_id — 1단계는 conversation_id 또는 ad-hoc.
    # 4단계 checkpoint/resume 도입 시 같은 thread_id 로 재진입한다.
    thread_id = fields.CharField(max_length=128, null=True)
    kind = fields.CharEnumField(enum_type=MLInferenceKind, default=MLInferenceKind.RISK_PREDICTION)
    status = fields.CharEnumField(enum_type=MLInferenceStatus, default=MLInferenceStatus.PENDING)
    # 입력 피처 — preprocess 노드의 출력 (BMI, age, 가족력 플래그, 측정값 등) 그대로 보존.
    input_features: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    # 결과 — 워커/노드가 채움. {"diabetes": {"score": 65.0, "level": "RISK"}, ...} 같은 dict.
    prediction_result: dict[str, Any] | None = fields.JSONField(null=True)  # type: ignore[assignment]
    # ML 모델 식별자 — 현재 룰 stub, 미래 실제 모델 버전.
    model_version = fields.CharField(max_length=40, default="risk-predictor-stub-v0")
    error_message = fields.TextField(null=True)
    duration_ms = fields.IntField(null=True)  # dispatch~결과 수신까지 (감사·SLA 분석용)
    created_at = fields.DatetimeField(auto_now_add=True)
    started_at = fields.DatetimeField(null=True)  # 실제 추론 시작 시각 (워커가 RUNNING 으로 옮길 때)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "ml_inference_requests"
        # 워커 큐 폴링 시 PENDING 빨리 찾기 위한 status+created 인덱스 (image_verification_jobs 패턴 동일)
        # + 사용자별 이력 조회용 user+created
        indexes = [
            ("status", "created_at"),
            ("user_id", "created_at"),
            ("kind", "status"),
        ]
