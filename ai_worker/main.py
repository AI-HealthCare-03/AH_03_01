"""ai_worker 의 진입점.

Redis 큐 `queue:image-verification` 을 BRPOP 으로 폴링하며,
SigLIP2 (google/siglip2-base-patch16-224, Apache 2.0) zero-shot 분류로
챌린지 카테고리에 맞는 사진인지 판정한다.

판정 결과를 다음 두 테이블에 반영:
- image_verification_jobs: status=SUCCESS/FAILED, result, completed_at
- challenge_verifications: status=APPROVED/REJECTED, rejection_reason

큐 메시지 포맷(JSON):
{
  "job_id": int,
  "verification_id": int,
  "file_id": int,
  "category": "WATER" | "EXERCISE" | ...,
  "sub_category": "WALKING" | "RUNNING" | ... | null
}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from tortoise import Tortoise

from ai_worker.tasks.category_prompts import (
    build_prompts_for,
    positive_count,
    threshold_for,
)
from ai_worker.tasks.image_classifier import SigLip2ZeroShotClassifier
from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.models.challenge import (
    ChallengeVerification,
    ImageVerificationJob,
    VerificationJobStatus,
    VerificationStatus,
)
from app.models.files import FileUpload
from app.models.pet import PointSource

logger = logging.getLogger("ai_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

QUEUE_KEY = config.IMAGE_VERIFY_QUEUE
THRESHOLD = config.SIGLIP_APPROVE_THRESHOLD
# positive_max 가 negative_max 보다 이 마진 이상으로 높아야 APPROVED.
# false-positive 방지: 모든 점수가 비슷하게 낮으면 거절.
POSITIVE_MARGIN = 0.05

_should_exit = False


def _install_signal_handlers() -> None:
    def _handler(signum: int, _frame: Any) -> None:
        global _should_exit
        logger.info("signal %s received, shutting down", signum)
        _should_exit = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


@asynccontextmanager
async def _tortoise_session():
    # ai_worker 는 마이그레이션 관리를 하지 않으므로 aerich.models 제외 후 init.
    # (ai 그룹에는 aerich 가 설치되지 않음)
    worker_config = {
        **TORTOISE_ORM,
        "apps": {
            "models": {
                "models": [m for m in TORTOISE_ORM["apps"]["models"]["models"] if m != "aerich.models"],
            },
        },
    }
    await Tortoise.init(config=worker_config)
    try:
        yield
    finally:
        await Tortoise.close_connections()


async def _process_message(classifier: SigLip2ZeroShotClassifier, payload: dict[str, Any]) -> None:
    job_id: int = int(payload["job_id"])
    verification_id: int = int(payload["verification_id"])
    file_id: int = int(payload["file_id"])
    category: str = str(payload.get("category") or "")
    sub_category: str | None = payload.get("sub_category")
    goal_config: dict = payload.get("goal_config") or {}

    job = await ImageVerificationJob.get_or_none(id=job_id)
    verification = await ChallengeVerification.get_or_none(id=verification_id)
    if job is None or verification is None:
        logger.warning("job/verification not found job_id=%s vid=%s", job_id, verification_id)
        return

    job.status = VerificationJobStatus.RUNNING
    job.started_at = datetime.now(config.TIMEZONE)
    await job.save(update_fields=["status", "started_at"])

    file_record = await FileUpload.get_or_none(id=file_id)
    if file_record is None or not os.path.exists(file_record.stored_path):
        await _fail_job(job, verification, reason=f"file_not_found id={file_id}")
        return

    prompts = build_prompts_for(category=category, sub_category=sub_category, goal_config=goal_config)
    if not prompts:
        await _fail_job(job, verification, reason=f"no_prompts_for_category={category}")
        return

    try:
        top_label, top_score, all_scores = classifier.classify(file_record.stored_path, prompts)
    except Exception as exc:  # noqa: BLE001
        logger.exception("classifier failed")
        await _fail_job(job, verification, reason=f"classifier_error: {exc}")
        return

    # 정책: build_prompts_for 결과는 [positive...] + [negative...] 순서이므로
    # 앞 N 개 = positive, 뒤 = negative 로 분리해 판정.
    n_pos = positive_count(category, sub_category, goal_config)
    positive_scores = [s["score"] for s in all_scores[:n_pos]] or [0.0]
    negative_scores = [s["score"] for s in all_scores[n_pos:]] or [0.0]
    p_max = max(positive_scores)
    n_max = max(negative_scores)
    category_threshold = threshold_for(category, THRESHOLD)
    approved = p_max >= category_threshold and p_max > n_max + POSITIVE_MARGIN

    result: dict[str, Any] = {
        "top_label": top_label,
        "top_score": top_score,
        "positive_max": p_max,
        "negative_max": n_max,
        "scores": all_scores,
        "threshold": category_threshold,
        "positive_margin": POSITIVE_MARGIN,
        "approved": approved,
    }

    now = datetime.now(config.TIMEZONE)
    job.status = VerificationJobStatus.SUCCESS
    job.result = result
    job.completed_at = now
    await job.save(update_fields=["status", "result", "completed_at"])

    if approved:
        verification.status = VerificationStatus.APPROVED
        verification.rejection_reason = None  # type: ignore[assignment]
        await verification.save(update_fields=["status", "rejection_reason"])
        await _grant_daily_reward_if_eligible(verification)
    else:
        verification.status = VerificationStatus.REJECTED
        verification.rejection_reason = (
            f"카테고리({category}) 매칭 점수 부족. "
            f"positive_max={p_max:.3f} negative_max={n_max:.3f} "
            f"threshold={category_threshold:.2f} margin={POSITIVE_MARGIN:.2f}"
        )
        await verification.save(update_fields=["status", "rejection_reason"])

    logger.info(
        "verification_id=%s category=%s pos_max=%.3f neg_max=%.3f threshold=%.2f approved=%s",
        verification_id,
        category,
        p_max,
        n_max,
        category_threshold,
        approved,
    )


async def _fail_job(job: ImageVerificationJob, verification: ChallengeVerification, *, reason: str) -> None:
    job.status = VerificationJobStatus.FAILED
    job.error_message = reason
    job.completed_at = datetime.now(config.TIMEZONE)
    await job.save(update_fields=["status", "error_message", "completed_at"])
    verification.status = VerificationStatus.REJECTED
    verification.rejection_reason = reason
    await verification.save(update_fields=["status", "rejection_reason"])
    logger.warning("job_id=%s failed: %s", job.id, reason)


async def _grant_daily_reward_if_eligible(verification: ChallengeVerification) -> None:
    """사진 인증이 APPROVED 로 확정되었을 때 데일리 보상을 지급한다."""
    import random

    from app.repositories.challenge_repository import ChallengeParticipantRepository
    from app.repositories.pet_repository import PointTransactionRepository

    participant_repo = ChallengeParticipantRepository()
    points = PointTransactionRepository()
    participant = await participant_repo.get(verification.participant_id)  # type: ignore[attr-defined]
    if participant is None:
        return
    await participant_repo.add_score(participant, points=1)
    amount = random.choice((50, 70, 100))
    await points.grant(
        user_id=verification.user_id,
        amount=amount,
        source=PointSource.CHALLENGE_DAILY,
        source_id=verification.id,
        description=f"챌린지 {verification.challenge_id} 사진 인증 보상",
    )


async def _main_loop() -> None:
    import redis.asyncio as redis_async

    classifier = SigLip2ZeroShotClassifier(model_name=config.SIGLIP_MODEL_NAME)
    classifier.warmup()

    client = redis_async.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        decode_responses=True,
    )
    logger.info("ai_worker started. queue=%s threshold=%.2f", QUEUE_KEY, THRESHOLD)

    while not _should_exit:
        try:
            popped = await client.brpop([QUEUE_KEY], timeout=5)  # type: ignore[misc]
        except Exception:  # noqa: BLE001
            logger.exception("redis brpop failed")
            await asyncio.sleep(2)
            continue
        if popped is None:
            continue
        _key, raw = popped
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("invalid queue payload: %s", raw)
            continue
        try:
            await _process_message(classifier, payload)
        except Exception:  # noqa: BLE001
            logger.exception("process_message failed for payload=%s", payload)

    logger.info("ai_worker stopped")


async def _entry() -> None:
    _install_signal_handlers()
    async with _tortoise_session():
        await _main_loop()


if __name__ == "__main__":
    asyncio.run(_entry())
