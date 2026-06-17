"""실패한 사진 인증(ImageVerificationJob) 재큐잉 스크립트.

배경:
    prod ai-worker 에 media_volume(/app/media) 마운트가 누락돼, fastapi 가 저장한
    인증 사진을 워커가 못 찾아(file_not_found) 모든 PHOTO 인증 잡이 FAILED →
    verification REJECTED 로 처리됐고, 달성률(APPROVED 만 집계)이 0% 로 남았다.
    compose 수정(ai-worker 에 media_volume:/app/media 추가) 배포 후에는 사진 파일이
    그대로 살아 있으므로, 실패한 잡을 다시 큐에 넣으면 워커가 정상 분류해
    정상 사진은 APPROVED 로 복구되고 보상도 지급된다.

⚠️ 선행조건: ai-worker 에 media_volume 마운트가 적용되어 워커가 /app/media 의
   파일을 볼 수 있는 상태에서 실행할 것. 마운트 적용 전 실행하면 또 file_not_found
   로 재실패한다(파괴적이지 않으니 마운트 후 다시 실행하면 됨).

안전장치:
    - 대상은 job.status == FAILED 인 잡뿐. SUCCESS/이미 APPROVED 된 건은 절대
      재큐하지 않는다 — 워커의 보상 지급(_grant_daily_reward_if_eligible)이 멱등성이
      없어, 이미 보상받은 인증을 재처리하면 포인트가 중복 지급되기 때문.
    - 연결된 verification 이 PHOTO 방식 + REJECTED + photo_file_id 존재 + 미삭제인
      건만 재큐(= 보상 미지급 상태가 확실한 건만).
    - 페이로드는 운영 코드와 동일한 enqueue_image_verification 헬퍼로 push(계약 일치).
    - --dry-run 으로 먼저 대상 건수/목록만 출력 가능(DB·큐 미변경).

멱등 실행: 재실행해도 FAILED 가 아닌(이미 재처리된) 잡은 자동 제외되므로 안전하다.

실행 방법 (prod EC2 컨테이너):
    docker cp scripts/requeue_failed_image_verifications.py fastapi:/tmp/requeue.py
    docker exec -i -w /app fastapi /app/.venv/bin/python /tmp/requeue.py --dry-run
    docker exec -i -w /app fastapi /app/.venv/bin/python /tmp/requeue.py

실행 방법 (로컬):
    docker exec -i fastapi uv run --no-sync python scripts/requeue_failed_image_verifications.py --dry-run
"""

import asyncio
import sys

from tortoise import Tortoise

from app.core.db.databases import TORTOISE_ORM
from app.core.queue import enqueue_image_verification
from app.models.challenge import (
    ImageVerificationJob,
    VerificationJobStatus,
    VerificationMethod,
    VerificationStatus,
)


async def _build_payload(job: ImageVerificationJob) -> dict | None:
    """재큐 대상이면 워커용 페이로드를, 아니면 None 을 반환.

    PHOTO + REJECTED + photo_file_id 존재 + 미삭제 인 건만 대상(= 보상 미지급 확정).
    """
    verification = await job.verification
    if verification is None:
        return None
    if verification.method != VerificationMethod.PHOTO:
        return None
    if verification.status != VerificationStatus.REJECTED:
        return None
    if verification.photo_file_id is None:
        return None
    if verification.is_deleted:
        return None

    challenge = await verification.challenge
    if challenge is None:
        return None

    return {
        "job_id": job.id,
        "verification_id": verification.id,
        "file_id": verification.photo_file_id,
        "category": challenge.category.value,
        "sub_category": challenge.sub_category.value if challenge.sub_category else None,
        "goal_config": challenge.goal_config or {},
    }


async def requeue(*, dry_run: bool) -> None:
    failed_jobs = await ImageVerificationJob.filter(status=VerificationJobStatus.FAILED).order_by("id")

    candidates: list[tuple[ImageVerificationJob, dict]] = []
    for job in failed_jobs:
        payload = await _build_payload(job)
        if payload is not None:
            candidates.append((job, payload))

    print(f"재큐 대상: {len(candidates)}건 (status=FAILED, PHOTO, REJECTED, 파일 존재)")
    for job, payload in candidates:
        print(
            f"  job#{job.id} verification#{payload['verification_id']} "
            f"file#{payload['file_id']} category={payload['category']}"
        )

    if dry_run:
        print("[dry-run] 변경 없이 종료. 실제 재큐하려면 --dry-run 없이 다시 실행.")
        return

    requeued = 0
    for job, payload in candidates:
        # 큐 push 가 성공한 잡만 DB 상태를 갱신해 큐/DB 정합을 유지.
        try:
            await enqueue_image_verification(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! job#{job.id} enqueue 실패, 건너뜀: {exc}")
            continue

        job.status = VerificationJobStatus.QUEUED
        job.error_message = None  # type: ignore[assignment]
        job.started_at = None  # type: ignore[assignment]
        job.completed_at = None  # type: ignore[assignment]
        await job.save(update_fields=["status", "error_message", "started_at", "completed_at"])

        # 재처리 동안 UI 가 '인증실패' 대신 '심사중' 으로 보이도록 verification 을 PENDING 으로.
        # 워커가 분류 완료 시 APPROVED/REJECTED 로 최종 확정한다.
        verification = await job.verification
        verification.status = VerificationStatus.PENDING
        verification.rejection_reason = None  # type: ignore[assignment]
        await verification.save(update_fields=["status", "rejection_reason"])
        requeued += 1

    print(f"완료 — {requeued}건 재큐(queue:image-verification). 워커가 순차 재처리한다.")


async def main() -> None:
    dry_run = "--dry-run" in sys.argv[1:]
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        await requeue(dry_run=dry_run)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
