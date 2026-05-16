"""SigLIP2 (google/siglip2-base-patch16-224, Apache 2.0) zero-shot 분류기.

Huggingface transformers 의 AutoModel/AutoProcessor 사용.
이미지 한 장 + 텍스트 프롬프트 리스트 → 각 프롬프트의 softmax 확률 → 최고 점수 매칭.

라이선스: Apache 2.0 (Google 공개) — 상업 이용/재배포/수정 자유.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger("ai_worker.siglip2")


class SigLip2ZeroShotClassifier:
    """모델 로딩은 비싸므로 프로세스 1회만. thread-safe 한 단순 lock 사용."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._lock = threading.Lock()
        self._model = None
        self._processor = None

    def warmup(self) -> None:
        """SigLIP2 모델/프로세서 사전 로드 (최초 호출 시 Huggingface 에서 다운로드)."""
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from transformers import AutoModel, AutoProcessor

            logger.info("loading SigLIP2 model=%s", self.model_name)
            self._processor = AutoProcessor.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.eval()
            logger.info("SigLIP2 ready")

    def classify(self, image_path: str, prompts: list[str]) -> tuple[str, float, list[dict[str, float]]]:
        """이미지를 프롬프트 후보와 비교해 가장 확률 높은 라벨을 반환.

        Returns: (top_label, top_score, [{"prompt": str, "score": float}, ...])
        """
        import torch
        from PIL import Image

        self._ensure_loaded()
        assert self._model is not None
        assert self._processor is not None

        image = Image.open(image_path).convert("RGB")
        inputs = self._processor(
            text=prompts,
            images=image,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
        )

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits_per_image = outputs.logits_per_image  # (1, len(prompts))
            probs = torch.softmax(logits_per_image, dim=-1)[0]

        score_list = [{"prompt": prompts[i], "score": float(probs[i].item())} for i in range(len(prompts))]
        top_idx = int(probs.argmax().item())
        return prompts[top_idx], float(probs[top_idx].item()), score_list
