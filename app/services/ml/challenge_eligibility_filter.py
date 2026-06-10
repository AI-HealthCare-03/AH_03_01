"""위험도 기반 챌린지 적합성 필터.

사용자 위험도·프로필에서 안전 제약과 우선순위 힌트를 추출하여
LLM 추천 프롬프트에 주입할 정보를 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.challenge import ChallengeCategory, ChallengeDifficulty, ExerciseSubType, RecommendationPriority
from app.models.health import DiseaseType, RiskLevel

# 위험도 수준 고위험 판단 임계
_HIGH_RISK_LEVELS = {RiskLevel.HIGH_RISK, RiskLevel.RISK}

# 고주강도 운동 서브타입 — 심혈관 고위험 시 제외 대상
_HIGH_INTENSITY_SUBTYPES = {ExerciseSubType.RUNNING, ExerciseSubType.CYCLING, ExerciseSubType.STRENGTH}
_HIGH_DIFFICULTY = {ChallengeDifficulty.LEVEL_3, ChallengeDifficulty.LEVEL_4}

# 위험 요인 → 권장 카테고리 (우선순위 순)
_RISK_FACTOR_CHALLENGE_MAP: dict[str, list[tuple[ChallengeCategory, str]]] = {
    "hypertension_high": [
        (ChallengeCategory.DIET, "저나트륨 식단은 혈압 관리 핵심 생활습관입니다."),
        (ChallengeCategory.EXERCISE, "규칙적인 유산소 운동이 혈압 강하에 효과적입니다."),
        (ChallengeCategory.NO_SMOKING, "흡연은 혈압 상승과 심혈관 위험을 높입니다."),
        (ChallengeCategory.SLEEP, "수면 부족은 혈압 조절을 어렵게 합니다."),
    ],
    "diabetes_high": [
        (ChallengeCategory.EXERCISE, "유산소+근력 운동 병행이 혈당 조절에 효과적입니다."),
        (ChallengeCategory.DIET, "탄수화물 조절 식단이 혈당 스파이크를 줄입니다."),
        (ChallengeCategory.WATER, "충분한 수분 섭취는 혈당 희석·신장 보호에 도움이 됩니다."),
        (ChallengeCategory.WEIGHT_MANAGEMENT, "체중 감량은 인슐린 저항성을 낮춥니다."),
    ],
    "cardiovascular_high": [
        (ChallengeCategory.NO_SMOKING, "금연은 심혈관 위험을 가장 빠르게 낮추는 방법입니다."),
        (ChallengeCategory.DIET, "LDL 감소를 위한 저포화지방 식단이 권고됩니다."),
        (ChallengeCategory.EXERCISE, "저~중강도 유산소 운동이 지질 프로필 개선에 도움이 됩니다."),
        (ChallengeCategory.SLEEP, "수면 부족은 심혈관 위험 인자와 연관됩니다."),
    ],
    "high_bmi": [
        (ChallengeCategory.WEIGHT_MANAGEMENT, "체중 감량으로 혈압·혈당·지질 모두 개선 가능합니다."),
        (ChallengeCategory.EXERCISE, "꾸준한 신체 활동이 체중 감량·유지에 핵심입니다."),
        (ChallengeCategory.DIET, "열량·탄수화물 조절 식단으로 체중을 관리합니다."),
    ],
    "is_smoker": [
        (ChallengeCategory.NO_SMOKING, "금연은 모든 만성질환 위험을 낮추는 1순위 생활습관 개선입니다."),
    ],
    "high_alcohol": [
        (ChallengeCategory.NO_ALCOHOL, "절주·금주는 혈압 조절과 간 건강에 중요합니다."),
    ],
}


@dataclass(slots=True)
class EligibleTemplate:
    template_id: int
    category: str
    sub_category: str | None
    title: str
    difficulty: str
    priority_hint: RecommendationPriority


@dataclass(slots=True)
class FilterResult:
    eligible_templates: list[EligibleTemplate] = field(default_factory=list)
    safety_notes: str = ""
    priority_reasons: list[str] = field(default_factory=list)


_DISEASE_FACTOR_KEY: dict[DiseaseType, str] = {
    DiseaseType.HYPERTENSION: "hypertension_high",
    DiseaseType.DIABETES: "diabetes_high",
    DiseaseType.CARDIOVASCULAR: "cardiovascular_high",
}


def _apply_prediction_factors(predictions: list[dict[str, Any]], factors: dict[str, bool]) -> None:
    for p in predictions:
        try:
            dt = DiseaseType(p["disease_type"])
            rl = RiskLevel(p["risk_level"])
        except (KeyError, ValueError):
            continue
        if rl in _HIGH_RISK_LEVELS:
            key = _DISEASE_FACTOR_KEY.get(dt)
            if key:
                factors[key] = True


def _extract_risk_factors(
    predictions: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, bool]:
    factors: dict[str, bool] = {
        "is_smoker": False,
        "high_alcohol": False,
        "high_bmi": False,
        "hypertension_high": False,
        "diabetes_high": False,
        "cardiovascular_high": False,
    }

    h = profile.get("height_cm")
    w = profile.get("weight_kg")
    if h and w and float(w) / ((float(h) / 100) ** 2) >= 25.0:
        factors["high_bmi"] = True

    if profile.get("current_smoker") == 1:
        factors["is_smoker"] = True

    if int(profile.get("alcohol_freq_y") or 0) >= 52:  # 주 1회 이상 (연 52회)
        factors["high_alcohol"] = True

    _apply_prediction_factors(predictions, factors)
    return factors


def _build_safety_notes(factors: dict[str, bool]) -> str:
    notes: list[str] = []
    if factors["cardiovascular_high"]:
        notes.append(
            "심혈관 고위험: 달리기·사이클·고강도 근력(LEVEL_3/4) 챌린지는 제외하고 "
            "저~중강도 유산소(걷기·수영 등)만 추천하세요."
        )
    return "\n".join(notes)


def _compute_priority(
    category: ChallengeCategory,
    factors: dict[str, bool],
) -> RecommendationPriority:
    """카테고리가 활성 위험요인과 몇 번 일치하는지로 우선순위 결정."""
    score = 0
    for factor_key, factor_active in factors.items():
        if not factor_active:
            continue
        for cat, _ in _RISK_FACTOR_CHALLENGE_MAP.get(factor_key, []):
            if cat == category:
                score += 1
                break
    if score >= 2:
        return RecommendationPriority.TOP
    if score == 1:
        return RecommendationPriority.RECOMMENDED
    return RecommendationPriority.OPTIONAL


def _is_safety_excluded(
    category: ChallengeCategory,
    sub_category: str | None,
    difficulty: str,
    factors: dict[str, bool],
) -> bool:
    if not factors["cardiovascular_high"]:
        return False
    if category != ChallengeCategory.EXERCISE:
        return False
    try:
        sub = ExerciseSubType(sub_category) if sub_category else None
        diff = ChallengeDifficulty(difficulty)
    except ValueError:
        return False
    if sub in _HIGH_INTENSITY_SUBTYPES and diff in _HIGH_DIFFICULTY:
        return True
    return False


async def filter_eligible_templates(
    predictions: list[dict[str, Any]],
    profile: dict[str, Any],
) -> FilterResult:
    """활성 ChallengeTemplate 중 사용자에게 적합한 후보와 안전 주의사항을 반환."""
    from app.models.challenge import ChallengeTemplate  # 지연 임포트 (Tortoise 초기화 보장)

    factors = _extract_risk_factors(predictions, profile)
    safety_notes = _build_safety_notes(factors)

    templates = await ChallengeTemplate.filter(is_active=True).all()

    eligible: list[EligibleTemplate] = []
    for t in templates:
        cat = ChallengeCategory(t.category)
        diff = str(t.difficulty)
        sub = str(t.sub_category) if t.sub_category else None

        if _is_safety_excluded(cat, sub, diff, factors):
            continue

        priority = _compute_priority(cat, factors)
        eligible.append(
            EligibleTemplate(
                template_id=t.id,
                category=str(cat),
                sub_category=sub,
                title=t.title,
                difficulty=diff,
                priority_hint=priority,
            )
        )

    # TOP 우선, 같으면 템플릿 ID 오름차순
    _priority_order = {RecommendationPriority.TOP: 0, RecommendationPriority.RECOMMENDED: 1, RecommendationPriority.OPTIONAL: 2}
    eligible.sort(key=lambda e: (_priority_order[e.priority_hint], e.template_id))

    priority_reasons: list[str] = []
    for factor_key, factor_active in factors.items():
        if not factor_active:
            continue
        for cat, reason in _RISK_FACTOR_CHALLENGE_MAP.get(factor_key, [])[:1]:
            priority_reasons.append(f"{cat}: {reason}")

    return FilterResult(eligible_templates=eligible, safety_notes=safety_notes, priority_reasons=priority_reasons)
