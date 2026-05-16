"""Disease-risk prediction integration boundary.

현재는 ai_worker 의 실제 모델이 준비되지 않아 룰 기반 계산기를 사용합니다.
ai_worker 의 모델 서비스가 준비되면 `RiskPredictor.predict` 의 본문만 HTTP 호출로 교체하면 됩니다.
호출 측(app) 은 본 모듈의 인터페이스(`PredictionInput`/`PredictionOutput`) 만 의존하므로,
모델 교체 시 라우터/서비스 코드 변경이 필요 없습니다.
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

    def to_dict(self) -> dict[str, Any]:
        return {"factor": self.factor, "weight": self.weight, "description": self.description}


@dataclass(slots=True)
class PredictionInput:
    disease_type: DiseaseType
    age: int | None = None
    gender: str | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    waist_cm: Decimal | None = None
    is_smoker: bool = False
    alcohol_intake: str | None = None
    has_diabetes_family_history: bool = False
    has_hypertension_family_history: bool = False
    is_chronic_patient: bool = False
    blood_pressure_systolic: Decimal | None = None
    blood_pressure_diastolic: Decimal | None = None
    fasting_glucose: Decimal | None = None
    postmeal_glucose: Decimal | None = None
    hba1c: Decimal | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "disease_type": self.disease_type.value,
            "age": self.age,
            "gender": self.gender,
            "height_cm": _as_float(self.height_cm),
            "weight_kg": _as_float(self.weight_kg),
            "waist_cm": _as_float(self.waist_cm),
            "is_smoker": self.is_smoker,
            "alcohol_intake": self.alcohol_intake,
            "has_diabetes_family_history": self.has_diabetes_family_history,
            "has_hypertension_family_history": self.has_hypertension_family_history,
            "is_chronic_patient": self.is_chronic_patient,
            "blood_pressure_systolic": _as_float(self.blood_pressure_systolic),
            "blood_pressure_diastolic": _as_float(self.blood_pressure_diastolic),
            "fasting_glucose": _as_float(self.fasting_glucose),
            "postmeal_glucose": _as_float(self.postmeal_glucose),
            "hba1c": _as_float(self.hba1c),
            **self.extra,
        }


@dataclass(slots=True)
class PredictionOutput:
    disease_type: DiseaseType
    risk_score: Decimal
    risk_level: RiskLevel
    contributing_factors: list[RiskFactor]
    model_version: str = "rule-v1"


def _as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


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
                "blood_pressure_systolic",
                _as_float(p.blood_pressure_systolic),
                140,
                40,
                "수축기 위험",
                120,
                20,
                "수축기 주의",
            ),
            _band(
                "blood_pressure_diastolic",
                _as_float(p.blood_pressure_diastolic),
                90,
                30,
                "이완기 위험",
                80,
                15,
                "이완기 주의",
            ),
        ]
        score, factors = _collect(bands)
        score, factors = _apply_flags(
            score,
            factors,
            [
                (p.has_hypertension_family_history, 10, "family_history", 0.1, "고혈압 가족력 있음"),
                (p.is_smoker, 7, "smoking", 0.07, "흡연자"),
                (p.alcohol_intake in {"MODERATE", "HEAVY"}, 5, "alcohol", 0.05, f"음주 빈도 {p.alcohol_intake}"),
                (p.age is not None and (p.age or 0) >= 50, 5, "age", 0.05, "50세 이상"),
            ],
        )
        return _build(DiseaseType.HYPERTENSION, score, factors)

    def _diabetes(self, p: PredictionInput) -> PredictionOutput:
        bands = [
            _band(
                "fasting_glucose",
                _as_float(p.fasting_glucose),
                126,
                35,
                "공복혈당 당뇨 의심",
                100,
                18,
                "공복혈당 전당뇨",
            ),
            _band(
                "postmeal_glucose",
                _as_float(p.postmeal_glucose),
                200,
                25,
                "식후혈당 당뇨 의심",
                140,
                12,
                "식후혈당 전당뇨",
            ),
            _band("hba1c", _as_float(p.hba1c), 6.5, 30, "HbA1c 당뇨 의심", 5.7, 15, "HbA1c 전당뇨"),
        ]
        score, factors = _collect(bands)
        bmi = _bmi(p.height_cm, p.weight_kg)
        score, factors = _apply_flags(
            score,
            factors,
            [
                (p.has_diabetes_family_history, 10, "family_history", 0.1, "당뇨 가족력 있음"),
                (bmi is not None and (bmi or 0) >= 25, 8, "bmi", 0.08, f"BMI {bmi:.1f} 비만" if bmi else "BMI 비만"),
            ],
        )
        return _build(DiseaseType.DIABETES, score, factors)

    def _cardiovascular(self, p: PredictionInput) -> PredictionOutput:
        score = 0.0
        factors: list[RiskFactor] = []
        sys_ = _as_float(p.blood_pressure_systolic)
        if sys_ is not None and sys_ >= 140:
            score += 25
            factors.append(RiskFactor("blood_pressure_systolic", 0.25, "수축기 혈압 위험 구간"))
        if p.is_smoker:
            score += 20
            factors.append(RiskFactor("smoking", 0.2, "흡연자"))
        bmi = _bmi(p.height_cm, p.weight_kg)
        if bmi is not None and bmi >= 25:
            score += 15
            factors.append(RiskFactor("bmi", 0.15, f"BMI {bmi:.1f}, 비만 구간"))
        if p.age is not None and p.age >= 50:
            score += 10
            factors.append(RiskFactor("age", 0.1, "50세 이상"))
        if p.has_hypertension_family_history or p.has_diabetes_family_history:
            score += 8
            factors.append(RiskFactor("family_history", 0.08, "가족력 있음"))
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
            factors.append(RiskFactor(factor, high_s / 100.0, f"{high_d} (값={value})"))
        elif value >= mid_t:
            score += mid_s
            factors.append(RiskFactor(factor, mid_s / 100.0, f"{mid_d} (값={value})"))
    return score, factors


def _apply_flags(
    score: float,
    factors: list[RiskFactor],
    flags: list[tuple[bool, float, str, float, str]],
) -> tuple[float, list[RiskFactor]]:
    for active, points, factor, weight, desc in flags:
        if active:
            score += points
            factors.append(RiskFactor(factor, weight, desc))
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
    """ai_worker 모델 호출의 단일 진입점.

    현재 구현: 룰 기반 폴백.
    향후: ai_worker HTTP 엔드포인트 호출로 대체. 실패 시 자동으로 룰 기반 결과 반환.
    """

    def __init__(self) -> None:
        self._fallback = RuleBasedRiskCalculator()

    async def predict(self, payload: PredictionInput) -> PredictionOutput:
        # TODO(ai_worker): 모델 서비스가 준비되면 여기서 HTTP/RPC 호출 후
        # 실패/타임아웃 시 self._fallback.calculate(payload) 로 폴백.
        return self._fallback.calculate(payload)
