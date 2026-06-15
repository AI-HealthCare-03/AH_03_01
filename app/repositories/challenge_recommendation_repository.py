"""ChallengeRecommendation DB 저장 헬퍼."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models.challenge import ChallengeRecommendation, RecommendationPriority

_PHI_PATTERN = re.compile(r"\d+\.?\d*\s*(?:mg(?:/dL)?|mmHg|kg|cm|%|kcal)", re.IGNORECASE)

_logger = logging.getLogger(__name__)

_VALID_PRIORITIES = {p.value for p in RecommendationPriority}


async def save_recommendations(
    user_id: Any,
    disease_risk_id: int | None,
    recommended: list[dict[str, Any]],
) -> list[int]:
    """recommended 목록을 challenge_recommendations 테이블에 저장하고 생성된 id 목록 반환.

    each item: {"template_id": int, "priority": str, "reason": str}
    """
    saved_ids: list[int] = []
    for item in recommended:
        template_id = item.get("template_id")
        if not isinstance(template_id, int) or template_id <= 0:
            continue
        priority_val = str(item.get("priority", RecommendationPriority.RECOMMENDED))
        if priority_val not in _VALID_PRIORITIES:
            priority_val = RecommendationPriority.RECOMMENDED
        reason = _PHI_PATTERN.sub("[값]", str(item.get("reason", "")))[:500] if item.get("reason") else None
        try:
            row = await ChallengeRecommendation.create(
                user_id=user_id,
                disease_risk_id=disease_risk_id,
                template_id=template_id,
                challenge_id=None,
                priority=priority_val,
                reason=reason,
            )
            saved_ids.append(row.id)
        except Exception:  # noqa: BLE001
            _logger.warning("챌린지 추천 저장 실패: template_id=%s", template_id)
    return saved_ids
