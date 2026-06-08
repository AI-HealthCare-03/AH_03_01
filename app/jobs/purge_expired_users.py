"""보관 기간(30일)이 지난 탈퇴 계정을 영구 파기하는 독립 실행 잡.

개인정보처리방침: 회원 탈퇴(soft delete) 후 ACCOUNT_RETENTION_DAYS(=30)일이 지난 계정은
복구 불가능한 방법으로 영구 파기한다. 이 스크립트가 그 파기를 실제로 수행한다.

파기 방식:
    대상 User row 를 하드 삭제한다. DB on_delete cascade 가 해당 유저의 PII/PHI
    (건강정보·기록·위험도·리포트·펫·포인트·챗봇세션 등) 를 함께 영구 제거한다.
    유저가 만든 챌린지(Challenge.creator)는 SET_NULL 로 보존되며 creator 만 NULL 이 된다.

대상 조건:
    is_deleted=True AND deleted_at <= (now - ACCOUNT_RETENTION_DAYS일)

실행(안전 기본값 — 인자 없이 실행하면 dry-run. 되돌릴 수 없는 영구 삭제는 --apply 명시 필요):
    python -m app.jobs.purge_expired_users                  # dry-run(기본): 대상만 로깅, 삭제 없음
    python -m app.jobs.purge_expired_users --apply          # 실제 영구 삭제 수행
    python -m app.jobs.purge_expired_users --apply --batch-size 50

외부 cron 으로 주기 실행한다(인앱 스케줄러 미사용). 예) 매일 04:00:
    0 4 * * *  cd /app && python -m app.jobs.purge_expired_users --apply >> /var/log/purge.log 2>&1
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta

from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.repositories.user_repository import UserRepository

# 보관 기간 상수는 auth.py 의 단일 정의를 재사용한다(중복 정의 금지).
from app.services.auth import ACCOUNT_RETENTION_DAYS

logger = logging.getLogger("app.jobs.purge_expired_users")

DEFAULT_BATCH_SIZE = 100


async def _delete_user_row(user_id: object) -> None:
    """단일 유저를 트랜잭션 안에서 하드 삭제한다(cascade 로 PII/PHI 동반 제거)."""
    repo = UserRepository()
    async with in_transaction():
        user = await repo.get_user(user_id)  # type: ignore[arg-type]  # UUID PK (스텁 차이)
        if user is None:  # 다른 프로세스가 이미 처리한 경우
            return
        await user.delete()


async def purge_expired_users(*, dry_run: bool, batch_size: int) -> dict[str, int]:
    """보관 기간이 지난 탈퇴 계정을 배치 단위로 하드 삭제한다.

    건별 예외는 격리해(실패가 전체를 막지 않음) 성공/실패 카운트를 집계한다.
    감사 추적: 시작/대상건수/성공·실패/소요시간을 logging 으로 남긴다(PII 미출력, user id 만).
    """
    repo = UserRepository()
    cutoff = datetime.now(config.TIMEZONE) - timedelta(days=ACCOUNT_RETENTION_DAYS)
    started = time.monotonic()

    logger.info(
        "purge 시작 dry_run=%s batch_size=%d retention_days=%d cutoff=%s",
        dry_run,
        batch_size,
        ACCOUNT_RETENTION_DAYS,
        cutoff.isoformat(),
    )

    # 전체 대상을 한 번에 조회(보관기간 만료 계정은 소량 가정). 배치는 삭제 단위에만 적용.
    targets = await repo.list_purgeable(cutoff)
    total = len(targets)
    logger.info("파기 대상 %d건", total)

    if dry_run:
        for user in targets:
            logger.info("[dry-run] 파기 대상 user_id=%s", user.id)
        elapsed = time.monotonic() - started
        logger.info("[dry-run] 종료 — 대상 %d건, 실제 삭제 없음, 소요 %.2fs", total, elapsed)
        return {"total": total, "purged": 0, "failed": 0}

    purged = 0
    failed = 0
    for batch_start in range(0, total, batch_size):
        batch = targets[batch_start : batch_start + batch_size]
        for user in batch:
            user_id = user.id
            try:
                await _delete_user_row(user_id)
                purged += 1
            except Exception:  # noqa: BLE001 — 건별 실패 격리: 한 건이 전체 파기를 막지 않도록
                failed += 1
                logger.exception("파기 실패 user_id=%s", user_id)
        logger.info(
            "배치 진행 %d/%d (성공 누적 %d, 실패 누적 %d)",
            min(batch_start + batch_size, total),
            total,
            purged,
            failed,
        )

    elapsed = time.monotonic() - started
    logger.info(
        "purge 완료 — 대상 %d건 / 성공 %d건 / 실패 %d건 / 소요 %.2fs",
        total,
        purged,
        failed,
        elapsed,
    )
    return {"total": total, "purged": purged, "failed": failed}


async def _run(*, dry_run: bool, batch_size: int) -> int:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        result = await purge_expired_users(dry_run=dry_run, batch_size=batch_size)
    finally:
        await Tortoise.close_connections()
    # 일부라도 실패했으면 비정상 종료코드로 cron/모니터링이 감지하도록 한다.
    return 1 if result["failed"] else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제 영구 삭제를 수행한다. 미지정 시 dry-run(기본 안전값) — 대상만 로깅하고 삭제하지 않음.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"대량 삭제 시 배치 처리 크기(기본 {DEFAULT_BATCH_SIZE}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args(argv)
    if args.batch_size < 1:
        logger.error("--batch-size 는 1 이상이어야 합니다 (입력값 %d)", args.batch_size)
        return 2
    # 안전 기본값: --apply 미지정이면 dry-run. 되돌릴 수 없는 영구 삭제이므로 실삭제는 명시 opt-in.
    return asyncio.run(_run(dry_run=not args.apply, batch_size=args.batch_size))


if __name__ == "__main__":
    sys.exit(main())
