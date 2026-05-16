"""챌린지 사진 인증용 SigLIP2 모델 통합 진입점.

현재는 ai_worker 모델 서버가 준비되지 않아 항상 PENDING 큐잉만 수행한다.
실제 모델이 준비되면 `ImageVerifier.run` 본문에서 ai_worker HTTP 호출로 결과를 받아
ImageVerificationJob 을 SUCCESS/FAILED 로 마무리한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ImageVerificationResult:
    success: bool
    confidence: float
    label: str | None
    raw: dict[str, Any]


class ImageVerifier:
    """사진 인증 ML 게이트웨이 스텁."""

    model_version = "siglip2-stub-v0"

    async def enqueue(self, *, verification_id: int, file_id: int) -> dict[str, Any]:
        # TODO(ai_worker): 메시지 브로커(Redis Stream)로 작업 푸시.
        return {
            "verification_id": verification_id,
            "file_id": file_id,
            "queued": True,
            "model_version": self.model_version,
        }

    async def run(self, *, file_id: int, category_hint: str | None = None) -> ImageVerificationResult:
        # TODO(ai_worker): SigLIP2 추론 호출. 임시로는 항상 보류(PENDING) 처리한다.
        return ImageVerificationResult(
            success=False,
            confidence=0.0,
            label=None,
            raw={"reason": "model_not_integrated_yet", "category_hint": category_hint},
        )
