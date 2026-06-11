"""RiskRecommendationGraph — LangGraph 기반 위험도 예측 + 맞춤 권고 그래프.

설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 2단계.

노드 흐름:
    validate_input (필수 데이터 검증 — DB 조회 결과 평가)
        ├ has_required_data=false → final_missing_info (CTA: 건강 정보 입력)
        └ true → preprocess (BMI 등 파생 변수 계산)
                    ↓
                    ml_inference (P1 동기: ml_inference_requests row + RiskPredictor 룰 stub 직접 호출
                                  미래: Redis 큐 dispatch + 워커 처리)
                    ↓
                    persist_disease_risk (DiseaseRisk 3 row 누적 — 시계열)
                    ↓
                    build_query (위험도 ≥ 50 질환을 diseases[] 필터로 보강)
                    ↓
                    retrieve (source_type=all, diseases[], 챌린지 카탈로그 함께)
                    ↓
                    generate_recommendation (시스템 프롬프트 — 위험도 결과 + 사용자 데이터 + 권고 + 챌린지)
                    ↓
                    evaluate (공용 medical_evaluator — Rule R1~R5 + LLM 6기준)
                    ↓
                    final_ok / generate(재생성) / rewrite_query / final_fallback

특징:
- ChatRAGGraph 와 동일한 evaluate · retrieve · prefilter·면책 정책 (의료 안전 일관).
- 매번 DB 자동 fetch (chatbot 후속 질문이 결과를 자연스럽게 활용 — DiseaseRisk 경유).
- ml_inference_requests 테이블·워커 골격은 3단계 비동기 전환을 위한 선행 인프라.

호출:
    result = await run_risk_recommendation(user_id=..., thread_id=...)
    # → RiskRecommendationResult dataclass (위험도 3개 + 권고 답변 + 챌린지 + sources)
"""

from __future__ import annotations

import functools
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI
from tortoise.transactions import in_transaction

from app.core import config
from app.graphs._shared.medical_evaluator import (
    EvalInput,
    EvalResultLiteral,
    EvalStageLiteral,
)
from app.graphs._shared.medical_evaluator import (
    evaluate as run_evaluator,
)
from app.models.health import (
    DiseaseRisk,
    DiseaseRiskGuideline,
    DiseaseType,
    HealthRecord,
    RecordType,
    RiskLevel,
    UserHealthInfo,
)
from app.models.ml_inference import (
    MLInferenceKind,
    MLInferenceRequest,
    MLInferenceStatus,
)
from app.repositories.challenge_recommendation_repository import save_recommendations
from app.services.ml.challenge_eligibility_filter import EligibleTemplate, filter_eligible_templates
from app.services.ml.retrieval import RetrievedChunk, retrieve
from app.services.ml.risk_predictor import (
    PredictionInput,
    PredictionOutput,
    RiskPredictor,
)

_logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 상수 / 정책
# ─────────────────────────────────────────────
MAX_REVISIONS = 2
RETRIEVE_TOP_K_MEDICAL = 8  # ChatRAGGraph 와 동일 — 4측면 커버
RISK_HIGH_THRESHOLD = 50.0  # diseases[] 필터로 retrieve 보강하는 임계 (팀원 CRAG 패턴)

MEDICAL_DISCLAIMER = (
    "본 결과는 의학적 진단이 아닌 참고용 위험도 지표입니다. 정확한 평가와 처방은 담당 의사 또는 약사와 상담하세요."
)
MISSING_INFO_MESSAGE = (
    "위험도 예측을 위해 건강 정보가 필요해요. 건강 정보 입력 페이지에서 키·몸무게·혈압·혈당 등을 입력해 주세요."
)
FALLBACK_MESSAGE = (
    "위험도 예측 결과는 산출됐으나 권고 메시지를 생성하는 데 어려움이 있었어요. "
    "구체적인 관리 방향은 담당 의사 또는 약사와 상담하시기를 권장합니다."
)

MODEL_VERSION = "risk-graph-v1"


# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────
DiseaseLiteral = Literal["diabetes", "hypertension", "dyslipidemia", "general"]
# DiseaseType.value 와 retrieve 의 diseases 필터 키 매핑 (소문자).
_DISEASE_KEY_MAP: dict[DiseaseType, str] = {
    DiseaseType.DIABETES: "diabetes",
    DiseaseType.HYPERTENSION: "hypertension",
    DiseaseType.CARDIOVASCULAR: "dyslipidemia",  # 심혈관·이상지질혈증 진료지침 같이 묶음
}


class RiskState(TypedDict, total=False):
    """RiskRecommendationGraph 노드 간 공유 상태."""

    # 입력
    user_id: Any
    thread_id: str

    # validate / fetch
    profile: dict[str, Any] | None
    recent_records: dict[str, dict[str, Any]]
    has_required_data: bool
    missing_fields: list[str]

    # preprocess
    feature_snapshot: dict[str, Any]  # PredictionInput.snapshot() 결과

    # ml_inference
    ml_request_ids: list[int]  # ml_inference_requests row ids
    predictions: list[dict[str, Any]]  # [{disease_type, risk_score, risk_level, factors}, ...]

    # persist_disease_risk
    disease_risk_row_ids: list[int]

    # retrieve / generate / evaluate (ChatRAGGraph 와 동일 패턴)
    retrieval_query: str
    retrieved_diseases: list[str]
    retrieved_docs: list[RetrievedChunk]
    draft_answer: str
    eval_result: EvalResultLiteral
    eval_stage: EvalStageLiteral
    eval_revision_count: int
    eval_feedback: str

    # challenge eligibility filter
    eligible_templates: list[EligibleTemplate]
    safety_notes: str
    recommended_challenges: list[dict[str, Any]]  # [{template_id, priority, reason}, ...]

    # final
    final_answer: str
    sources: list[RetrievedChunk]
    is_fallback: bool
    error: str | None


# ─────────────────────────────────────────────
# 결과 타입 (그래프 외부 반환용)
# ─────────────────────────────────────────────
@dataclass(slots=True)
class PredictionSummary:
    disease_type: str  # "DIABETES" / "HYPERTENSION" / "CARDIOVASCULAR"
    risk_score: float
    risk_level: str  # "NORMAL"/"CAUTION"/"RISK"/"HIGH_RISK"
    contributing_factors: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class RiskRecommendationResult:
    answer: str  # 권고·챌린지 추천 본문 (LLM 생성)
    predictions: list[PredictionSummary] = field(default_factory=list)
    sources: list[RetrievedChunk] = field(default_factory=list)
    has_required_data: bool = True
    missing_fields: list[str] = field(default_factory=list)
    is_fallback: bool = False
    eval_revision_count: int | None = None
    disclaimer: str = MEDICAL_DISCLAIMER
    model_version: str = MODEL_VERSION


# ─────────────────────────────────────────────
# OpenAI 클라이언트 / 유틸 (ChatRAGGraph 와 동일 패턴)
# ─────────────────────────────────────────────
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 가 비어 있어 RiskRecommendationGraph 를 실행할 수 없습니다.")
        _client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.OPENAI_REQUEST_TIMEOUT,
            max_retries=config.OPENAI_MAX_RETRIES,
        )
    return _client


def _safe_err_repr(e: BaseException) -> str:
    head = str(e).splitlines()[0] if str(e) else ""
    return f"{type(e).__name__}: {head[:160]}"


def _timed_node(func: Callable[[RiskState], Awaitable[dict[str, Any]]]) -> Any:
    """ChatRAGGraph 와 동일 패턴 — 노드별 timing 로그."""

    @functools.wraps(func)
    async def wrapper(state: RiskState) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            return await func(state)
        finally:
            _logger.info("[node:%s] %.0fms", func.__name__, (time.perf_counter() - t0) * 1000)

    return wrapper


# ─────────────────────────────────────────────
# 노드 1: validate_input (DB 자동 fetch + 필수 데이터 검증)
# ─────────────────────────────────────────────
async def validate_input(state: RiskState) -> dict[str, Any]:
    """사용자 건강 정보를 DB 에서 자동 fetch 하고 필수 필드 검증.

    최소 요구: UserHealthInfo 의 height_cm + weight_kg (BMI 계산용).
    추가로 측정값(혈압/혈당)이 있으면 더 정교한 위험도 산출.
    """
    user_id = state.get("user_id")
    if not user_id:
        return {"has_required_data": False, "missing_fields": ["user_id"]}

    profile = await UserHealthInfo.filter(user_id=user_id).first()
    if profile is None or (profile.height_cm is None and profile.weight_kg is None):
        return {
            "profile": None,
            "recent_records": {},
            "has_required_data": False,
            "missing_fields": ["height_cm", "weight_kg"],
        }

    # 각 record_type 별 최근 1건 (ChatRAGGraph 의 fetch_health_data 와 같은 패턴)
    recent: dict[str, dict[str, Any]] = {}
    for rt in RecordType:
        rec = (
            await HealthRecord.filter(user_id=user_id, record_type=rt, is_deleted=False)
            .order_by("-measured_at")
            .first()
        )
        if rec is None:
            continue
        recent[rt.value] = {
            "primary_value": float(rec.primary_value),
            "secondary_value": float(rec.secondary_value) if rec.secondary_value is not None else None,
            "unit": rec.unit,
            "sub_type": str(rec.sub_type) if rec.sub_type else None,
            "measured_at": rec.measured_at.isoformat(),
        }

    profile_dict = {
        "height_cm": float(profile.height_cm) if profile.height_cm is not None else None,
        "weight_kg": float(profile.weight_kg) if profile.weight_kg is not None else None,
        "waist_cm": float(profile.waist_cm) if profile.waist_cm is not None else None,
        "systolic_bp": float(profile.systolic_bp) if profile.systolic_bp is not None else None,
        "diastolic_bp": float(profile.diastolic_bp) if profile.diastolic_bp is not None else None,
        "fasting_blood_sugar": (
            float(profile.fasting_blood_sugar) if profile.fasting_blood_sugar is not None else None
        ),
        "sleep_weekday": float(profile.sleep_weekday) if profile.sleep_weekday is not None else None,
        "sleep_weekend": float(profile.sleep_weekend) if profile.sleep_weekend is not None else None,
        "moderate_exercise_hour": (
            float(profile.moderate_exercise_hour) if profile.moderate_exercise_hour is not None else None
        ),
        "smoking_risk": float(profile.smoking_risk) if profile.smoking_risk is not None else None,
        "mid_act_day": profile.mid_act_day,
        "walk_day": profile.walk_day,
        "water_count": profile.water_count,
        "family_dm": profile.family_dm,
        "family_hp": profile.family_hp,
        "family_hl": profile.family_hl,
        "current_smoker": profile.current_smoker,
        "alcohol_freq_y": profile.alcohol_freq_y,
        "alcohol_cup": profile.alcohol_cup,
        "fruit_freq": profile.fruit_freq,
        "veg_freq_1": profile.veg_freq_1,
        "out_meal_freq": profile.out_meal_freq,
        "breakfast_freq": profile.breakfast_freq,
        "is_menopause": profile.is_menopause,
        "ocp_total_months": profile.ocp_total_months,
        "anemia": profile.anemia,
        "chronic_diseases": list(profile.chronic_diseases) if profile.chronic_diseases else [],
        "medications": list(profile.medications) if profile.medications else [],
    }
    return {
        "profile": profile_dict,
        "recent_records": recent,
        "has_required_data": True,
        "missing_fields": [],
    }


def decide_after_validate(state: RiskState) -> Literal["preprocess", "final_missing_info"]:
    return "preprocess" if state.get("has_required_data") else "final_missing_info"


async def final_missing_info(state: RiskState) -> dict[str, Any]:
    return {
        "final_answer": MISSING_INFO_MESSAGE,
        "sources": [],
        "is_fallback": False,
        "predictions": [],
        "disease_risk_row_ids": [],
        "retrieved_docs": [],
    }


# ─────────────────────────────────────────────
# 노드 2: preprocess (파생 변수)
# ─────────────────────────────────────────────
def _to_dec(v: float | None) -> Decimal | None:
    return Decimal(str(v)) if v is not None else None


def _is_frequent_alcohol_freq(alcohol_freq_y: int | None) -> bool:
    """KNHANES BD1_11 코드(1=거의매일…7=전혀안함, -1=모름)로 잦은 음주(주 1회 이상) 여부."""
    if alcohol_freq_y is None or alcohol_freq_y <= 0:
        return False
    return 1 <= alcohol_freq_y <= 3


def _family_history_labels(profile: dict[str, Any]) -> list[str]:
    """가족력 코드(1=있음)를 표시용 라벨 목록으로. (-1=모름/0=없음 은 제외)"""
    labels: list[str] = []
    if profile.get("family_dm") == 1:
        labels.append("당뇨")
    if profile.get("family_hp") == 1:
        labels.append("고혈압")
    if profile.get("family_hl") == 1:
        labels.append("고지혈증")
    return labels


async def preprocess(state: RiskState) -> dict[str, Any]:
    """프로필 + 최근 측정값을 PredictionInput 호환 dict 로 정리."""
    profile = state.get("profile") or {}
    recent = state.get("recent_records") or {}
    # 혈압: BLOOD_PRESSURE 의 primary=수축기, secondary=이완기 (인덱싱 시 약속).
    # 프로필(UserHealthInfo)에 값이 없으면 최근 측정값(HealthRecord)으로 보완.
    bp = recent.get("BLOOD_PRESSURE", {})
    glu = recent.get("BLOOD_GLUCOSE", {})

    snapshot = {
        "height_cm": profile.get("height_cm"),
        "weight_kg": profile.get("weight_kg"),
        "waist_cm": profile.get("waist_cm"),
        "systolic_bp": profile.get("systolic_bp")
        if profile.get("systolic_bp") is not None
        else bp.get("primary_value"),
        "diastolic_bp": (
            profile.get("diastolic_bp") if profile.get("diastolic_bp") is not None else bp.get("secondary_value")
        ),
        "fasting_blood_sugar": (
            profile.get("fasting_blood_sugar")
            if profile.get("fasting_blood_sugar") is not None
            else (glu.get("primary_value") if glu.get("sub_type") in (None, "FASTING") else None)
        ),
        "sleep_weekday": profile.get("sleep_weekday"),
        "sleep_weekend": profile.get("sleep_weekend"),
        "moderate_exercise_hour": profile.get("moderate_exercise_hour"),
        "smoking_risk": profile.get("smoking_risk"),
        "mid_act_day": profile.get("mid_act_day"),
        "walk_day": profile.get("walk_day"),
        "water_count": profile.get("water_count"),
        "family_dm": profile.get("family_dm"),
        "family_hp": profile.get("family_hp"),
        "family_hl": profile.get("family_hl"),
        "current_smoker": profile.get("current_smoker"),
        "alcohol_freq_y": profile.get("alcohol_freq_y"),
        "alcohol_cup": profile.get("alcohol_cup"),
        "fruit_freq": profile.get("fruit_freq"),
        "veg_freq_1": profile.get("veg_freq_1"),
        "out_meal_freq": profile.get("out_meal_freq"),
        "breakfast_freq": profile.get("breakfast_freq"),
        "is_menopause": profile.get("is_menopause"),
        "ocp_total_months": profile.get("ocp_total_months"),
        "anemia": profile.get("anemia"),
    }
    return {"feature_snapshot": snapshot}


# ─────────────────────────────────────────────
# 노드 3: ml_inference (P1 동기 — RiskPredictor 룰 stub + ml_inference_requests row)
# ─────────────────────────────────────────────
_predictor = RiskPredictor()


def _build_prediction_input(disease_type: DiseaseType, snapshot: dict[str, Any]) -> PredictionInput:
    return PredictionInput(
        disease_type=disease_type,
        height_cm=_to_dec(snapshot.get("height_cm")),
        weight_kg=_to_dec(snapshot.get("weight_kg")),
        waist_cm=_to_dec(snapshot.get("waist_cm")),
        systolic_bp=_to_dec(snapshot.get("systolic_bp")),
        diastolic_bp=_to_dec(snapshot.get("diastolic_bp")),
        fasting_blood_sugar=_to_dec(snapshot.get("fasting_blood_sugar")),
        sleep_weekday=_to_dec(snapshot.get("sleep_weekday")),
        sleep_weekend=_to_dec(snapshot.get("sleep_weekend")),
        moderate_exercise_hour=_to_dec(snapshot.get("moderate_exercise_hour")),
        smoking_risk=_to_dec(snapshot.get("smoking_risk")),
        mid_act_day=snapshot.get("mid_act_day"),
        walk_day=snapshot.get("walk_day"),
        water_count=snapshot.get("water_count"),
        family_dm=snapshot.get("family_dm"),
        family_hp=snapshot.get("family_hp"),
        family_hl=snapshot.get("family_hl"),
        current_smoker=snapshot.get("current_smoker"),
        alcohol_freq_y=snapshot.get("alcohol_freq_y"),
        alcohol_cup=snapshot.get("alcohol_cup"),
        fruit_freq=snapshot.get("fruit_freq"),
        veg_freq_1=snapshot.get("veg_freq_1"),
        out_meal_freq=snapshot.get("out_meal_freq"),
        breakfast_freq=snapshot.get("breakfast_freq"),
        is_menopause=snapshot.get("is_menopause"),
        ocp_total_months=snapshot.get("ocp_total_months"),
        anemia=snapshot.get("anemia"),
    )


async def ml_inference(state: RiskState) -> dict[str, Any]:
    """3개 질환 (당뇨/고혈압/심혈관) 위험도 산출.

    각 질환마다 ml_inference_requests row 1개 생성 + RiskPredictor 동기 호출 +
    결과 row 채움. P1 패턴 — 미래 ML 학습 완료 시 dispatch 부분만 Redis 큐로 교체.
    """
    user_id = state.get("user_id")
    thread_id = state.get("thread_id")
    snapshot = state.get("feature_snapshot") or {}

    request_ids: list[int] = []
    predictions: list[dict[str, Any]] = []

    for dt in (DiseaseType.DIABETES, DiseaseType.HYPERTENSION, DiseaseType.CARDIOVASCULAR):
        t_start = time.perf_counter()
        payload = _build_prediction_input(dt, snapshot)
        request = await MLInferenceRequest.create(
            user_id=user_id,
            thread_id=thread_id,
            kind=MLInferenceKind.RISK_PREDICTION,
            status=MLInferenceStatus.RUNNING,
            input_features=payload.snapshot(),
            model_version="risk-predictor-stub-v0",
            started_at=datetime.now(tz=UTC),
        )
        try:
            output: PredictionOutput = await _predictor.predict(payload)
            duration_ms = int((time.perf_counter() - t_start) * 1000)
            result_dict = {
                "disease_type": output.disease_type.value,
                "risk_score": float(output.risk_score),
                "risk_level": output.risk_level.value,
                "contributing_factors": [f.to_dict() for f in output.contributing_factors],
                "model_version": output.model_version,
            }
            request.status = MLInferenceStatus.SUCCESS
            request.prediction_result = result_dict
            request.duration_ms = duration_ms
            request.completed_at = datetime.now(tz=UTC)
            await request.save()
            request_ids.append(request.id)
            predictions.append(result_dict)
        except Exception as e:  # noqa: BLE001
            _logger.warning("ml_inference (%s) 실패: %s", dt.value, type(e).__name__)
            _logger.debug("ml_inference (%s) 실패 상세: %s", dt.value, _safe_err_repr(e))
            request.status = MLInferenceStatus.FAILED
            request.error_message = _safe_err_repr(e)
            request.completed_at = datetime.now(tz=UTC)
            await request.save()
            # 부분 실패 — 해당 질환만 skip, 다른 질환 계속

    return {"ml_request_ids": request_ids, "predictions": predictions}


# ─────────────────────────────────────────────
# 노드 4: persist_disease_risk (DiseaseRisk 이력 누적 저장)
# ─────────────────────────────────────────────
async def persist_disease_risk(state: RiskState) -> dict[str, Any]:
    """예측 결과를 DiseaseRisk 테이블에 시계열 row 로 누적.

    각 질환별 1 row. guideline_id 는 (disease_type, risk_level) 매칭으로 자동 연결.
    이후 ChatRAGGraph 의 fetch_health_data 가 자동으로 이 결과를 컨텍스트로 활용.
    """
    user_id = state.get("user_id")
    predictions = state.get("predictions") or []
    snapshot = state.get("feature_snapshot") or {}

    # H-3: 같은 호출의 3 disease persist 를 한 트랜잭션으로 묶어 부분 실패 시
    # row 가 일부만 남는 일관성 깨짐을 차단. (노드 간 gap — ml_inference SUCCESS
    # 후 그래프 crash 시나리오는 backlog: monitoring 으로 보정 예정.)
    row_ids: list[int] = []
    async with in_transaction():
        for p in predictions:
            try:
                disease_type = DiseaseType(p["disease_type"])
                risk_level = RiskLevel(p["risk_level"])
            except (KeyError, ValueError):
                continue
            # guideline 매칭 (없으면 null)
            guideline = await DiseaseRiskGuideline.filter(disease_type=disease_type, risk_level=risk_level).first()
            row = await DiseaseRisk.create(
                user_id=user_id,
                disease_type=disease_type,
                risk_score=Decimal(str(p["risk_score"])),
                risk_level=risk_level,
                contributing_factors=p.get("contributing_factors") or [],
                input_snapshot=snapshot,
                model_version=p.get("model_version", "rule-v1"),
                guideline_id=guideline.id if guideline else None,
            )
            row_ids.append(row.id)
    return {"disease_risk_row_ids": row_ids}


# ─────────────────────────────────────────────
# 노드 5: build_query (위험도 ≥ 50 질환을 retrieve 필터로 보강)
# ─────────────────────────────────────────────
async def build_query(state: RiskState) -> dict[str, Any]:
    """위험도 기반 RAG 검색 쿼리·필터 생성.

    팀원 CRAG 패턴 (`prediction ≥ 50 → 쿼리 보강`) 재사용.
    - 고위험 질환 키워드를 쿼리에 명시
    - retrieve.diseases 필터로 해당 진료지침 우선 매칭
    """
    predictions = state.get("predictions") or []
    high_risk_keywords: list[str] = []
    diseases: list[str] = []
    for p in predictions:
        score = float(p.get("risk_score", 0) or 0)
        if score < RISK_HIGH_THRESHOLD:
            continue
        try:
            dt = DiseaseType(p["disease_type"])
        except (KeyError, ValueError):
            continue
        key = _DISEASE_KEY_MAP.get(dt)
        if key and key not in diseases:
            diseases.append(key)
        if dt == DiseaseType.HYPERTENSION:
            high_risk_keywords.append("고혈압 생활습관 관리")
        elif dt == DiseaseType.DIABETES:
            high_risk_keywords.append("당뇨 생활습관 관리")
        elif dt == DiseaseType.CARDIOVASCULAR:
            high_risk_keywords.append("이상지질혈증 심혈관 관리")

    # 위험도가 모두 낮으면 일반 생활습관 + 챌린지 추천 컨텍스트.
    base_query = "만성질환 예방을 위한 생활습관 관리와 챌린지 추천"
    if high_risk_keywords:
        query = base_query + " — 중점: " + " / ".join(high_risk_keywords)
    else:
        query = base_query

    # 챌린지 적합성 필터 — 안전 제약 + 우선순위 힌트
    profile = state.get("profile") or {}
    try:
        filter_result = await filter_eligible_templates(predictions, profile)
    except Exception as e:  # noqa: BLE001
        _logger.warning("ChallengeEligibilityFilter 실패, 빈 결과로 진행: %s", _safe_err_repr(e))
        from app.services.ml.challenge_eligibility_filter import FilterResult

        filter_result = FilterResult()

    return {
        "retrieval_query": query,
        "retrieved_diseases": diseases,
        "eligible_templates": filter_result.eligible_templates,
        "safety_notes": filter_result.safety_notes,
    }


# ─────────────────────────────────────────────
# 노드 6: retrieve (source_type=all — 진료지침 + 챌린지 카탈로그 + 서비스 가이드)
# ─────────────────────────────────────────────
async def retrieve_node(state: RiskState) -> dict[str, Any]:
    query = state.get("retrieval_query") or "만성질환 예방 생활습관"
    diseases = state.get("retrieved_diseases") or []
    try:
        # 위험도 권고는 진료지침(diseases 필터) + 챌린지 카탈로그 둘 다 필요 → source_type=all.
        result = await retrieve(
            query=query,
            top_k=RETRIEVE_TOP_K_MEDICAL,
            source_type="all",
            disease=diseases if diseases else None,
        )
    except Exception as e:  # noqa: BLE001
        _logger.warning("retrieve 실패, 빈 결과로 진행: %s", _safe_err_repr(e))
        return {"retrieved_docs": [], "error": _safe_err_repr(e)}
    return {"retrieved_docs": result.chunks}


# ─────────────────────────────────────────────
# 노드 7: generate_recommendation
# ─────────────────────────────────────────────
_RECOMMENDATION_SYSTEM = """당신은 만성질환(고혈압·당뇨·이상지질혈증) 위험도 평가 결과를 바탕으로
사용자에게 맞춤 생활습관 권고와 챌린지를 안내하는 한국어 의료 챗봇입니다.

규칙:
1. [위험도 예측 결과] 블록의 수치·등급을 답변 본문에 그대로 인용 (예: "당뇨 위험도 65점,
   RISK 등급으로 평가됨"). 모호한 일반론 금지.
2. **수치·정량 권고 필수** (의료 완전성):
   - 관리 목표 (예: "LDL-C 100 mg/dL 미만", "수축기 혈압 140 mmHg 미만")
   - 생활요법 (예: "나트륨 하루 2,400 mg 미만", "유산소 운동 주 5~7회 30분 이상")
   - 추적 검사 주기 (예: "지질 검사 매년 1회 이상")
3. **의료 4측면 모두 다루기** (해당 컨텍스트 있으면):
   (a) 관리 목표 (b) 생활요법 (c) 약물치료 일반 원칙 (d) 추적 관리
4. [사용자 건강 정보] 블록의 실제 수치(BMI/혈압/혈당 등) 를 본문에 명시 인용.
5. [챌린지 카탈로그] 자료에 정의된 챌린지만 추천. 사용자 위험도 + 데이터에 매핑된
   **구체 목표 예시**(예: "주 5일 30분 걷기 챌린지") 포함. 카탈로그 외 임의 챌린지 절대 생성 금지.
6. 절대 단정적 진단/위험 등급 부여 금지 ("당신은 당뇨입니다" 같은 표현 금지).
   "위험도 RISK 등급" 같은 평가 시스템 출력은 그대로 인용 가능.
7. 약물 복용 결정·용량·특정 약 직접 권고 절대 금지.
8. 답변 끝에 반드시 "정확한 평가와 처방은 담당 의사 또는 약사와 상담하세요" 권고 포함.
9. 답변은 명확하고 간결하게. 불릿/문단 구성으로 읽기 좋게.

답변 구조 권장:
- 위험도 요약 (3개 질환 결과 인용)
- 핵심 권고 (4측면 중 해당 항목)
- 챌린지 추천 (카탈로그 매핑, 구체 목표 예시 1~3개)
- 의사 상담 권고
"""


def _format_predictions_block(predictions: list[dict[str, Any]]) -> str:
    if not predictions:
        return "[위험도 예측 결과]\n(예측 결과 없음)\n\n"
    lines = ["[위험도 예측 결과 — 진단 아님, 참고용]"]
    for p in predictions:
        score = float(p.get("risk_score", 0) or 0)
        lines.append(f"- {p.get('disease_type', '?')}: 점수 {score:.1f}, 등급 {p.get('risk_level', '?')}")
        factors = p.get("contributing_factors") or []
        if factors:
            top = [f.get("description") for f in factors[:3] if f.get("description")]
            if top:
                lines.append(f"    기여 요인: {', '.join(top)}")
    return "\n".join(lines) + "\n\n"


def _format_user_profile_block(state: RiskState) -> str:
    profile = state.get("profile") or {}
    recent = state.get("recent_records") or {}
    if not profile and not recent:
        return ""
    lines = ["[사용자 건강 정보 — 진단 아님, 참고용]"]
    h = profile.get("height_cm")
    w = profile.get("weight_kg")
    if h and w:
        bmi = float(w) / ((float(h) / 100) ** 2)
        lines.append(f"- 키 {h}cm, 몸무게 {w}kg, BMI {bmi:.1f}")
    if profile.get("waist_cm"):
        lines.append(f"- 허리둘레 {profile['waist_cm']}cm")
    if profile.get("current_smoker") == 1:
        lines.append("- 현재 흡연")
    if _is_frequent_alcohol_freq(profile.get("alcohol_freq_y")):
        lines.append("- 잦은 음주 빈도")
    fam = _family_history_labels(profile)
    if fam:
        lines.append(f"- 가족력: {', '.join(fam)}")
    for rt, rec in recent.items():
        v = rec.get("primary_value")
        v2 = rec.get("secondary_value")
        unit = rec.get("unit", "")
        val = f"{v}/{v2}" if v2 is not None else f"{v}"
        lines.append(f"- 최근 {rt}: {val} {unit}")
    return "\n".join(lines) + "\n\n"


def _format_context(docs: list[RetrievedChunk]) -> str:
    """retrieve 결과를 LLM 입력용 텍스트로 (medical_evaluator.format_context 와 동일 포맷)."""
    if not docs:
        return "(검색된 컨텍스트가 없습니다.)"
    parts: list[str] = []
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        title = d.title or meta.get("section_title") or d.source
        pages = meta.get("source_pages")
        header = f"[자료 {i}] 출처: {d.source}" + (f" / p.{pages}" if pages else "") + f" — {title}"
        parts.append(header + "\n" + d.chunk_text)
    return "\n\n".join(parts)


def _format_eligible_templates_block(eligible: list[EligibleTemplate]) -> str:
    if not eligible:
        return ""
    lines = ["[추천 가능 챌린지 템플릿 — 이 목록에 있는 template_id 만 추천 가능]"]
    for t in eligible:
        sub = f" / {t.sub_category}" if t.sub_category else ""
        lines.append(f"- id={t.template_id}  {t.title}  ({t.category}{sub}, {t.difficulty}, 우선도 힌트: {t.priority_hint})")
    return "\n".join(lines) + "\n\n"


def _parse_recommendation_json(draft: str) -> tuple[str, list[dict[str, Any]]]:
    """draft 에서 <!--RECS:[...]–-> 블록을 추출하고 clean 본문과 파싱된 목록을 반환."""
    import re

    pattern = r"<!--RECS:(\[[\s\S]*?\])-->"
    m = re.search(pattern, draft)
    if not m:
        return draft, []
    json_str = m.group(1)
    clean = draft[: m.start()].rstrip() + draft[m.end():]
    try:
        items = json.loads(json_str)
        if not isinstance(items, list):
            items = []
    except Exception:  # noqa: BLE001
        items = []
    return clean.strip(), items


async def generate_recommendation(state: RiskState) -> dict[str, Any]:
    predictions = state.get("predictions") or []
    docs = state.get("retrieved_docs") or []
    # H-5: 빈 컨텍스트면 LLM 호출 skip — evaluator R1 가 retrieval_problem 으로
    # 잡아 rewrite/fallback 라우팅. (ChatRAG 와 동일 정책)
    if not docs:
        _logger.info("generate_recommendation skip — retrieved_docs 비어있음 (evaluator R1 위임)")
        return {"draft_answer": ""}
    feedback = state.get("eval_feedback", "")
    feedback_hint = f"\n\n[Evaluator 피드백] 이전 답변에서 보완할 점: {feedback}" if feedback else ""

    eligible: list[EligibleTemplate] = state.get("eligible_templates") or []
    safety_notes = state.get("safety_notes") or ""

    safety_block = f"[안전 제약 — 반드시 준수]\n{safety_notes}\n\n" if safety_notes else ""
    templates_block = _format_eligible_templates_block(eligible)

    allowed_ids = {t.template_id for t in eligible}
    json_instruction = (
        "\n\n답변 본문 작성 후, 아래 형식으로 추천 챌린지 JSON 블록을 **반드시** 본문 끝에 붙이세요 "
        "(템플릿 목록의 id 만 사용, 최대 3개):\n"
        '<!--RECS:[{"template_id": <id>, "priority": "TOP"|"RECOMMENDED"|"OPTIONAL", "reason": "한국어 한 줄 이유"}]-->'
    ) if allowed_ids else ""

    user_prompt = (
        f"{_format_predictions_block(predictions)}"
        f"{_format_user_profile_block(state)}"
        f"{safety_block}"
        f"{templates_block}"
        f"컨텍스트(진료지침 + 챌린지 카탈로그):\n{_format_context(docs)}\n\n"
        f"위 정보를 사용해 한국어로 위험도 요약 + 권고 + 챌린지 추천을 작성하세요."
        f"{json_instruction}"
        f"{feedback_hint}"
    )

    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _RECOMMENDATION_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        draft = (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        _logger.warning("generate_recommendation 실패: %s", _safe_err_repr(e))
        return {"draft_answer": "", "error": _safe_err_repr(e)}

    # JSON 추천 블록 추출 (whitelist 검증 포함)
    eligible = state.get("eligible_templates") or []
    allowed_ids = {t.template_id for t in eligible}
    clean_draft, raw_recs = _parse_recommendation_json(draft)
    validated_recs = [r for r in raw_recs if isinstance(r.get("template_id"), int) and r["template_id"] in allowed_ids]

    return {"draft_answer": clean_draft, "recommended_challenges": validated_recs}


# ─────────────────────────────────────────────
# 노드 8: evaluate (공용 medical_evaluator)
# ─────────────────────────────────────────────
async def evaluate_node(state: RiskState) -> dict[str, Any]:
    # 위험도 답변은 사용자 데이터 + 위험도 결과 인용을 명시적으로 강제하므로
    # health_data 블록도 함께 전달 (R5 검사용 — 사용자 실제 수치 인용 여부).
    health_data = {
        "profile": state.get("profile") or {},
        "recent_records": state.get("recent_records") or {},
    }
    has_health_data = bool(state.get("profile") or state.get("recent_records"))
    inp = EvalInput(
        question="위험도 예측 결과를 바탕으로 사용자에게 맞춤 권고를 제공",
        draft=state.get("draft_answer", ""),
        docs=state.get("retrieved_docs", []),
        intent="medical_inquiry",  # 위험도 권고는 medical 영역
        has_health_data=has_health_data,
        health_data=health_data if has_health_data else None,
        revision_count=int(state.get("eval_revision_count", 0)),
    )
    out = await run_evaluator(inp)
    return {
        "eval_result": out.eval_result,
        "eval_stage": out.eval_stage,
        "eval_revision_count": out.eval_revision_count,
        "eval_feedback": out.eval_feedback,
    }


def decide_after_evaluate(
    state: RiskState,
) -> Literal["final_ok", "generate_recommendation", "build_query", "final_fallback"]:
    eval_result: EvalResultLiteral = state.get("eval_result", "pass")  # type: ignore[assignment]
    revision_count = int(state.get("eval_revision_count", 0))
    if eval_result == "pass":
        return "final_ok"
    if revision_count >= MAX_REVISIONS:
        return "final_fallback"
    if eval_result == "generation_problem":
        return "generate_recommendation"
    # retrieval_problem → build_query 재실행 (위험도 기반 쿼리 재구성)
    return "build_query"


# ─────────────────────────────────────────────
# 노드 9: final_ok / final_fallback
# ─────────────────────────────────────────────
async def final_ok(state: RiskState) -> dict[str, Any]:
    # 챌린지 추천 DB 저장
    recommended = state.get("recommended_challenges") or []
    if recommended:
        user_id = state.get("user_id")
        risk_ids = state.get("disease_risk_row_ids") or []
        disease_risk_id = risk_ids[0] if risk_ids else None
        try:
            await save_recommendations(user_id, disease_risk_id, recommended)
        except Exception as e:  # noqa: BLE001
            _logger.warning("챌린지 추천 저장 실패: %s", _safe_err_repr(e))
            return {
                "final_answer": state.get("draft_answer", ""),
                "sources": state.get("retrieved_docs", []),
                "is_fallback": True,
            }

    return {
        "final_answer": state.get("draft_answer", ""),
        "sources": state.get("retrieved_docs", []),
        "is_fallback": False,
    }


async def final_fallback(state: RiskState) -> dict[str, Any]:
    return {
        "final_answer": FALLBACK_MESSAGE,
        "sources": [],
        "is_fallback": True,
    }


# ─────────────────────────────────────────────
# 그래프 컴파일
# ─────────────────────────────────────────────
def _build_graph() -> Any:
    g: StateGraph[RiskState] = StateGraph(RiskState)
    g.add_node("validate_input", _timed_node(validate_input))
    g.add_node("final_missing_info", _timed_node(final_missing_info))
    g.add_node("preprocess", _timed_node(preprocess))
    g.add_node("ml_inference", _timed_node(ml_inference))
    g.add_node("persist_disease_risk", _timed_node(persist_disease_risk))
    g.add_node("build_query", _timed_node(build_query))
    g.add_node("retrieve", _timed_node(retrieve_node))
    g.add_node("generate_recommendation", _timed_node(generate_recommendation))
    g.add_node("evaluate", _timed_node(evaluate_node))
    g.add_node("final_ok", _timed_node(final_ok))
    g.add_node("final_fallback", _timed_node(final_fallback))

    g.add_edge(START, "validate_input")
    g.add_conditional_edges(
        "validate_input",
        decide_after_validate,
        {"preprocess": "preprocess", "final_missing_info": "final_missing_info"},
    )
    g.add_edge("preprocess", "ml_inference")
    g.add_edge("ml_inference", "persist_disease_risk")
    g.add_edge("persist_disease_risk", "build_query")
    g.add_edge("build_query", "retrieve")
    g.add_edge("retrieve", "generate_recommendation")
    g.add_edge("generate_recommendation", "evaluate")
    g.add_conditional_edges(
        "evaluate",
        decide_after_evaluate,
        {
            "final_ok": "final_ok",
            "generate_recommendation": "generate_recommendation",
            "build_query": "build_query",
            "final_fallback": "final_fallback",
        },
    )
    g.add_edge("final_missing_info", END)
    g.add_edge("final_ok", END)
    g.add_edge("final_fallback", END)
    return g.compile()


_compiled_graph: Any | None = None


def RiskRecommendationGraph() -> Any:  # noqa: N802 — API 계약 명칭 보존
    """컴파일된 그래프 (lazy singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


# ─────────────────────────────────────────────
# 공개 진입점
# ─────────────────────────────────────────────
async def run_risk_recommendation(
    user_id: Any,
    thread_id: str | None = None,
) -> RiskRecommendationResult:
    """RiskRecommendationGraph 1회 실행 → RiskRecommendationResult.

    Args:
        user_id: 인증된 사용자 id (DB 자동 fetch)
        thread_id: LangGraph thread (선택, ad-hoc 가능)
    """
    graph = RiskRecommendationGraph()
    initial: RiskState = {
        "user_id": user_id,
        "thread_id": thread_id or f"risk-{user_id}-{int(time.time())}",
        "eval_revision_count": 0,
    }
    try:
        final_state: RiskState = await graph.ainvoke(initial)
    except Exception as e:  # noqa: BLE001
        _logger.error("RiskRecommendationGraph 실행 실패: %s", _safe_err_repr(e))
        return RiskRecommendationResult(
            answer=FALLBACK_MESSAGE,
            is_fallback=True,
        )

    if not final_state.get("has_required_data", True):
        return RiskRecommendationResult(
            answer=MISSING_INFO_MESSAGE,
            has_required_data=False,
            missing_fields=list(final_state.get("missing_fields", [])),
            predictions=[],
            sources=[],
            is_fallback=False,
        )

    return RiskRecommendationResult(
        answer=final_state.get("final_answer", FALLBACK_MESSAGE),
        predictions=[
            PredictionSummary(
                disease_type=str(p.get("disease_type", "?")),
                risk_score=float(p.get("risk_score", 0) or 0),
                risk_level=str(p.get("risk_level", "?")),
                contributing_factors=list(p.get("contributing_factors") or []),
            )
            for p in (final_state.get("predictions") or [])
        ],
        sources=list(final_state.get("sources") or []),
        is_fallback=bool(final_state.get("is_fallback", False)),
        eval_revision_count=int(final_state.get("eval_revision_count", 0)),
    )


# ChatRAGGraph 의 __init__ 과 함께 export
__all__ = [
    "MAX_REVISIONS",
    "MEDICAL_DISCLAIMER",
    "MISSING_INFO_MESSAGE",
    "PredictionSummary",
    "RISK_HIGH_THRESHOLD",
    "RiskRecommendationGraph",
    "RiskRecommendationResult",
    "RiskState",
    "run_risk_recommendation",
]


# ChatRAGGraph 모듈의 _logger json import 충돌 회피 (no-op).
_ = json
