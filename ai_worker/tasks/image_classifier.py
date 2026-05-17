"""SigLIP2 (google/siglip2-base-patch16-224, Apache 2.0) zero-shot 분류기.

Huggingface transformers 의 AutoModel/AutoProcessor 사용.
이미지 한 장 + 텍스트 프롬프트 리스트 → 각 프롬프트의 softmax 확률 → 매칭 점수.

라이선스: Apache 2.0 (Google 공개) — 상업 이용/재배포/수정 자유.

GPU 자동 감지: CUDA > MPS(Apple Metal) > CPU. 환경변수 SIGLIP_DEVICE 로 강제 가능.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger("ai_worker.siglip2")


def _autodetect_device() -> str:
    """가능한 가장 빠른 device 반환. SIGLIP_DEVICE 환경변수로 override 가능."""
    forced = os.getenv("SIGLIP_DEVICE", "").strip().lower()
    if forced in {"cuda", "mps", "cpu"}:
        return forced
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class SigLip2ZeroShotClassifier:
    """모델 로딩은 비싸므로 프로세스 1회만. thread-safe 한 단순 lock 사용."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._lock = threading.Lock()
        self._model = None
        self._processor = None
        self._device: str | None = None

    @property
    def device(self) -> str:
        if self._device is None:
            self._device = _autodetect_device()
        return self._device

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

            logger.info("loading SigLIP2 model=%s device=%s", self.model_name, self.device)
            self._processor = AutoProcessor.from_pretrained(self.model_name)
            model = AutoModel.from_pretrained(self.model_name)
            model.eval()
            try:
                model = model.to(self.device)
            except Exception as exc:  # noqa: BLE001 — device 이동 실패 시 CPU 폴백
                logger.warning("failed moving model to %s (%s) — falling back to cpu", self.device, exc)
                self._device = "cpu"
                model = model.to("cpu")
            self._model = model
            logger.info("SigLIP2 ready on %s", self.device)

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
        # 입력 tensor 들도 동일 device 로 이동
        inputs = {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits_per_image = outputs.logits_per_image  # (1, len(prompts))
            probs = torch.softmax(logits_per_image, dim=-1)[0].cpu()

        score_list = [{"prompt": prompts[i], "score": float(probs[i].item())} for i in range(len(prompts))]
        top_idx = int(probs.argmax().item())
        return prompts[top_idx], float(probs[top_idx].item()), score_list
