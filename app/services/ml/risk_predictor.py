"""Disease-risk prediction integration boundary.

현재는 ai_worker 의 실제 모델이 준비되지 않아 룰 기반 계산기를 사용합니다.
ai_worker 의 모델 서비스가 준비되면 `RiskPredictor.predict` 의 본문만 HTTP 호출로 교체하면 됩니다.
호출 측(app) 은 본 모듈의 인터페이스(`PredictionInput`/`PredictionOutput`) 만 의존하므로,
모델 교체 시 라우터/서비스 코드 변경이 필요 없습니다.

입력 필드는 KNHANES 예측 모델 28입력(v2 스키마, `UserHealthInfo`) 컬럼명과 동일합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.models.health import DiseaseType, RiskLevel


@dataclass(slots=True)
class RiskFactor:
    factor: str
    weight: float
    description: str | None = None
    name_kor: str | None = None  # 사람이 읽는 한글명 (ML 경로만; 룰 폴백은 None)
    direction: str | None = None  # "위험 증가↑"/"위험 감소↓" (없으면 weight 부호로 파생)

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": self.factor,
            "weight": self.weight,
            "description": self.description,
            "name_kor": self.name_kor,
            "direction": self.direction or ("위험 증가↑" if self.weight > 0 else "위험 감소↓"),
        }


@dataclass(slots=True)
class PredictionInput:
    disease_type: DiseaseType
    age: int | None = None
    gender: str | None = None
    # 수치형 (Decimal)
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    waist_cm: Decimal | None = None
    systolic_bp: Decimal | None = None
    diastolic_bp: Decimal | None = None
    fasting_blood_sugar: Decimal | None = None
    sleep_weekday: Decimal | None = None
    sleep_weekend: Decimal | None = None
    moderate_exercise_hour: Decimal | None = None
    smoking_risk: Decimal | None = None
    # 활동/섭취 (int)
    mid_act_day: int | None = None
    walk_day: int | None = None
    water_count: int | None = None
    # 가족력 (1=있음/0=없음/-1=모름)
    family_dm: int | None = None
    family_hp: int | None = None
    family_hl: int | None = None
    # 흡연 (현재흡연=1/비흡연=0)
    current_smoker: int | None = None
    # 음주/식습관 (KNHANES 코드)
    alcohol_freq_y: int | None = None
    alcohol_cup: int | None = None
    fruit_freq: int | None = None
    veg_freq_1: int | None = None
    out_meal_freq: int | None = None
    breakfast_freq: int | None = None
    # 폐경/호르몬/기타 (폐경=1/비폐경여성=0/남성·비해당=-1)
    is_menopause: int | None = None
    ocp_total_months: int | None = None
    anemia: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "disease_type": self.disease_type.value,
            "age": self.age,
            "gender": self.gender,
            "height_cm": _as_float(self.height_cm),
            "weight_kg": _as_float(self.weight_kg),
            "waist_cm": _as_float(self.waist_cm),
            "systolic_bp": _as_float(self.systolic_bp),
            "diastolic_bp": _as_float(self.diastolic_bp),
            "fasting_blood_sugar": _as_float(self.fasting_blood_sugar),
            "sleep_weekday": _as_float(self.sleep_weekday),
            "sleep_weekend": _as_float(self.sleep_weekend),
            "moderate_exercise_hour": _as_float(self.moderate_exercise_hour),
            "smoking_risk": _as_float(self.smoking_risk),
            "mid_act_day": self.mid_act_day,
            "walk_day": self.walk_day,
            "water_count": self.water_count,
            "family_dm": self.family_dm,
            "family_hp": self.family_hp,
            "family_hl": self.family_hl,
            "current_smoker": self.current_smoker,
            "alcohol_freq_y": self.alcohol_freq_y,
            "alcohol_cup": self.alcohol_cup,
            "fruit_freq": self.fruit_freq,
            "veg_freq_1": self.veg_freq_1,
            "out_meal_freq": self.out_meal_freq,
            "breakfast_freq": self.breakfast_freq,
            "is_menopause": self.is_menopause,
            "ocp_total_months": self.ocp_total_months,
            "anemia": self.anemia,
            **self.extra,
        }


@dataclass(slots=True)
class PredictionOutput:
    disease_type: DiseaseType
    risk_score: Decimal
    risk_level: RiskLevel
    contributing_factors: list[RiskFactor]
    model_version: str = "rule-v1"


_FACTOR_KOR: dict[str, str] = {
    "systolic_bp": "수축기 혈압",
    "diastolic_bp": "이완기 혈압",
    "fasting_blood_sugar": "공복혈당",
    "bmi": "BMI",
    "age": "나이",
    "smoking": "흡연",
    "alcohol": "음주 빈도",
    "family_history": "가족력",
}


def _as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _is_frequent_drinker(alcohol_freq_y: int | None) -> bool:
    """KNHANES BD1_11 연간 음주 빈도 코드로 '잦은 음주' 판단.

    코드: 1=거의매일 … 7=전혀안함, -1=모름. 잦음(1~3: 주 1회 이상)이면 위험 가중.
    None/-1(모름)/0 은 가중 없음(안전 스킵).
    """
    if alcohol_freq_y is None or alcohol_freq_y <= 0:
        return False
    return 1 <= alcohol_freq_y <= 3


# 룰 기반 위험도 계산 (KSH 2022 / KDA 2023 기준값 사용)
# ai_worker 의 실제 ML 모델이 준비되기 전까지의 폴백 구현이다.
class RuleBasedRiskCalculator:
    """판정 기준값(CLAUDE.md 명시) 기반 위험도 산출기."""

    def calculate(self, payload: PredictionInput) -> PredictionOutput:
        if payload.disease_type == DiseaseType.HYPERTENSION:
            return self._hypertension(payload)
        if payload.disease_type == DiseaseType.DIABETES:
            return self._diabetes(payload)
        return self._cardiovascular(payload)

    def _hypertension(self, p: PredictionInput) -> PredictionOutput:
        bands = [
            _band(
                "systolic_bp",
                _as_float(p.systolic_bp),
                140,
                40,
                "수축기 혈압이 위험 수준으로 고혈압 위험을 높이고 있어요",
                120,
                20,
                "수축기 혈압이 주의 수준이에요, 생활습관 개선이 필요해요",
            ),
            _band(
                "diastolic_bp",
                _as_float(p.diastolic_bp),
                90,
                30,
                "이완기 혈압이 위험 수준으로 고혈압 위험을 높이고 있어요",
                80,
                15,
                "이완기 혈압이 주의 수준이에요, 꾸준한 관리가 필요해요",
            ),
        ]
        score, factors = _collect(bands)
        score, factors = _apply_flags(
            score,
            factors,
            [
                (p.family_hp == 1, 10, "family_history", 0.1, "고혈압 가족력이 발병 위험을 높이고 있어요"),
                (p.current_smoker == 1, 7, "smoking", 0.07, "흡연이 혈압을 높여 고혈압 위험을 키우고 있어요"),
                (_is_frequent_drinker(p.alcohol_freq_y), 5, "alcohol", 0.05, "잦은 음주가 고혈압 위험을 높이고 있어요"),
                (p.age is not None and (p.age or 0) >= 50, 5, "age", 0.05, "나이가 많을수록 위험도가 높아져요"),
            ],
        )
        return _build(DiseaseType.HYPERTENSION, score, factors)

    def _diabetes(self, p: PredictionInput) -> PredictionOutput:
        bands = [
            _band(
                "fasting_blood_sugar",
                _as_float(p.fasting_blood_sugar),
                126,
                35,
                "공복혈당이 당뇨 기준을 초과해 적극적인 관리가 필요해요",
                100,
                18,
                "공복혈당이 전당뇨 수준으로 생활습관 개선이 중요해요",
            ),
        ]
        score, factors = _collect(bands)
        bmi = _bmi(p.height_cm, p.weight_kg)
        score, factors = _apply_flags(
            score,
            factors,
            [
                (p.family_dm == 1, 10, "family_history", 0.1, "당뇨 가족력이 발병 위험을 높이고 있어요"),
                (bmi is not None and (bmi or 0) >= 25, 8, "bmi", 0.08, f"BMI {bmi:.1f}로 비만 구간에 있어 당뇨 위험을 높이고 있어요" if bmi else "비만이 당뇨 위험을 높이고 있어요"),
            ],
        )
        return _build(DiseaseType.DIABETES, score, factors)

    def _cardiovascular(self, p: PredictionInput) -> PredictionOutput:
        score = 0.0
        factors: list[RiskFactor] = []
        sys_ = _as_float(p.systolic_bp)
        if sys_ is not None and sys_ >= 140:
            score += 25
            factors.append(RiskFactor("systolic_bp", 0.25, "수축기 혈압이 위험 수준으로 심혈관 위험을 높이고 있어요", name_kor=_FACTOR_KOR.get("systolic_bp")))
        if p.current_smoker == 1:
            score += 20
            factors.append(RiskFactor("smoking", 0.2, "흡연이 심혈관 위험을 크게 높이고 있어요", name_kor=_FACTOR_KOR.get("smoking")))
        bmi = _bmi(p.height_cm, p.weight_kg)
        if bmi is not None and bmi >= 25:
            score += 15
            factors.append(RiskFactor("bmi", 0.15, f"BMI {bmi:.1f}로 비만 구간에 있어 심혈관 위험을 높이고 있어요", name_kor=_FACTOR_KOR.get("bmi")))
        if p.age is not None and p.age >= 50:
            score += 10
            factors.append(RiskFactor("age", 0.1, "나이가 많을수록 심혈관 위험이 높아져요", name_kor=_FACTOR_KOR.get("age")))
        if p.family_hp == 1 or p.family_dm == 1 or p.family_hl == 1:
            score += 8
            factors.append(RiskFactor("family_history", 0.08, "가족력이 심혈관 위험을 높이고 있어요", name_kor=_FACTOR_KOR.get("family_history")))
        return PredictionOutput(
            disease_type=DiseaseType.CARDIOVASCULAR,
            risk_score=Decimal(str(min(round(score, 2), 100.0))),
            risk_level=_score_to_level(score),
            contributing_factors=factors,
        )


def _band(
    factor: str,
    value: float | None,
    high_threshold: float,
    high_score: float,
    high_desc: str,
    mid_threshold: float,
    mid_score: float,
    mid_desc: str,
) -> tuple[str, float | None, float, float, str, float, float, str]:
    return (factor, value, high_threshold, high_score, high_desc, mid_threshold, mid_score, mid_desc)


def _collect(
    bands: list[tuple[str, float | None, float, float, str, float, float, str]],
) -> tuple[float, list[RiskFactor]]:
    score = 0.0
    factors: list[RiskFactor] = []
    for factor, value, high_t, high_s, high_d, mid_t, mid_s, mid_d in bands:
        if value is None:
            continue
        if value >= high_t:
            score += high_s
            factors.append(RiskFactor(factor, high_s / 100.0, high_d, name_kor=_FACTOR_KOR.get(factor)))
        elif value >= mid_t:
            score += mid_s
            factors.append(RiskFactor(factor, mid_s / 100.0, mid_d, name_kor=_FACTOR_KOR.get(factor)))
    return score, factors


def _apply_flags(
    score: float,
    factors: list[RiskFactor],
    flags: list[tuple[bool, float, str, float, str]],
) -> tuple[float, list[RiskFactor]]:
    for active, points, factor, weight, desc in flags:
        if active:
            score += points
            factors.append(RiskFactor(factor, weight, desc, name_kor=_FACTOR_KOR.get(factor)))
    return score, factors


def _build(disease_type: DiseaseType, score: float, factors: list[RiskFactor]) -> PredictionOutput:
    return PredictionOutput(
        disease_type=disease_type,
        risk_score=Decimal(str(min(round(score, 2), 100.0))),
        risk_level=_score_to_level(score),
        contributing_factors=factors,
    )


def _bmi(height_cm: Decimal | None, weight_kg: Decimal | None) -> float | None:
    if not height_cm or not weight_kg:
        return None
    h = float(height_cm) / 100.0
    if h <= 0:
        return None
    return float(weight_kg) / (h * h)


def _score_to_level(score: float) -> RiskLevel:
    if score >= 70:
        return RiskLevel.HIGH_RISK
    if score >= 45:
        return RiskLevel.RISK
    if score >= 20:
        return RiskLevel.CAUTION
    return RiskLevel.NORMAL


class RiskPredictor:
    """ML 모델 기반 위험도 예측 진입점.

    ML 모델 로드 실패 시 룰 기반 폴백으로 자동 전환.
    호출 측은 PredictionInput / PredictionOutput 인터페이스만 의존.
    """

    def __init__(self) -> None:
        self._fallback = RuleBasedRiskCalculator()
        self._ml: Any | None = None
        self._ml_loaded = False

    def _get_ml(self) -> Any | None:
        """MLRiskPredictor 지연 로드 (최초 호출 시 1회)"""
        if self._ml_loaded:
            return self._ml
        try:
            from app.services.ml.ml_risk_predictor_draft import MLRiskPredictor

            self._ml = MLRiskPredictor()
            self._ml._lazy_load()  # 아티팩트 로드 검증
        except Exception:
            self._ml = None
        self._ml_loaded = True
        return self._ml

    async def predict(self, payload: PredictionInput) -> PredictionOutput:
        import logging
        import traceback

        logger = logging.getLogger(__name__)
        ml = self._get_ml()
        if ml is not None:
            try:
                return ml.calculate(payload)
            except Exception as e:
                logger.error(f"[MLRiskPredictor] calculate 실패: {type(e).__name__}: {e}")
                logger.error(traceback.format_exc())
        return self._fallback.calculate(payload)
