"""위험도 기반 챌린지 추천기.

LLM 기반 추천이 준비되기 전까지의 룰 기반 폴백.
DiseaseRisk 의 disease_type / risk_level / contributing_factors 를 보고
ChallengeTemplate 풀에서 카테고리 매핑으로 후보를 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.challenge import ChallengeCategory, ExerciseSubType, RecommendationPriority
from app.models.health import DiseaseType, RiskLevel


@dataclass(slots=True)
class RecommendationHint:
    category: ChallengeCategory
    sub_category: ExerciseSubType | None
    priority: RecommendationPriority
    reason: str


_DISEASE_CATEGORY_PRIORITY: dict[DiseaseType, list[tuple[ChallengeCategory, ExerciseSubType | None]]] = {
    DiseaseType.HYPERTENSION: [
        (ChallengeCategory.EXERCISE, ExerciseSubType.WALKING),
        (ChallengeCategory.DIET, None),
        (ChallengeCategory.NO_SMOKING, None),
        (ChallengeCategory.SLEEP, None),
    ],
    DiseaseType.DIABETES: [
        (ChallengeCategory.EXERCISE, ExerciseSubType.WALKING),
        (ChallengeCategory.DIET, None),
        (ChallengeCategory.WATER, None),
        (ChallengeCategory.MEDITATION, None),
    ],
    DiseaseType.CARDIOVASCULAR: [
        (ChallengeCategory.EXERCISE, ExerciseSubType.RUNNING),
        (ChallengeCategory.NO_SMOKING, None),
        (ChallengeCategory.DIET, None),
        (ChallengeCategory.SLEEP, None),
    ],
}


_LEVEL_TO_PRIORITY = {
    RiskLevel.HIGH_RISK: RecommendationPriority.TOP,
    RiskLevel.RISK: RecommendationPriority.TOP,
    RiskLevel.CAUTION: RecommendationPriority.RECOMMENDED,
    RiskLevel.NORMAL: RecommendationPriority.OPTIONAL,
}


class ChallengeRecommender:
    def hints_for(self, disease_type: DiseaseType, risk_level: RiskLevel, limit: int = 3) -> list[RecommendationHint]:
        # TODO(ai_worker): 추후 LLM 기반 개인화 추천 결과로 대체.
        base_priority = _LEVEL_TO_PRIORITY.get(risk_level, RecommendationPriority.OPTIONAL)
        order = _DISEASE_CATEGORY_PRIORITY.get(disease_type, [])
        hints: list[RecommendationHint] = []
        for idx, (category, sub) in enumerate(order[:limit]):
            priority = base_priority if idx == 0 else RecommendationPriority.RECOMMENDED
            hints.append(
                RecommendationHint(
                    category=category,
                    sub_category=sub,
                    priority=priority,
                    reason=f"{disease_type.value} 위험도 {risk_level.value} 대응 권장 카테고리",
                )
            )
        return hints
