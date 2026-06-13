"""기간이 종료된 챌린지를 COMPLETED 상태로 일괄 전환하는 독립 실행 잡.

end_date < 오늘인 ACTIVE/RECRUITING 챌린지는 백엔드 status 가 실제 종료 상태를
반영하지 못한다. 이 잡이 매일 실행되어 DB 를 실제 상태와 일치시킨다.

대상 조건:
    status IN (ACTIVE, RECRUITING) AND end_date < today

실행(안전 기본값 — 인자 없이 실행하면 dry-run. 실제 업데이트는 --apply 명시 필요):
    python -m app.jobs.complete_expired_challenges                   # dry-run: 대상만 로깅
    python -m app.jobs.complete_expired_challenges --apply           # 실제 status 업데이트
    python -m app.jobs.complete_expired_challenges --apply --batch-size 50

외부 cron 으로 주기 실행한다(인앱 스케줄러 미사용). 예) 매일 KST 자정(UTC 15:00):
    0 15 * * *  cd /app && python -m app.jobs.complete_expired_challenges --apply >> /var/log/complete_challenges.log 2>&1
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import date

from tortoise import Tortoise

from app.core.db.databases import TORTOISE_ORM
from app.models.challenge import Challenge, ChallengeParticipant, ChallengeScope, ChallengeStatus, GoalType, ParticipantStatus
from app.models.pet import PointSource, PointTransaction
from app.services.rewards import RewardService

logger = logging.getLogger("app.jobs.complete_expired_challenges")

DEFAULT_BATCH_SIZE = 100


_reward_service = RewardService()


def _group_goal_achieved(challenge: Challenge, participants: list[ChallengeParticipant]) -> bool:
    """그룹 챌린지 목표 달성 여부를 반환한다."""
    cfg = challenge.goal_config or {}
    if challenge.goal_type == GoalType.GROUP_SUM:
        total = sum(p.current_score for p in participants)
        target = cfg.get("group_target_count", 0)
        return total >= target
    else:  # GROUP_MEMBERS
        achieved = sum(1 for p in participants if p.current_score >= 1)
        target = cfg.get("group_target_members", 0)
        return achieved >= target


async def _grant_completion_rewards(challenge: Challenge) -> None:
    """챌린지 완료 시 APPROVED 참여자에게 보상을 자동 지급한다. 중복 지급 방지."""
    participants = await ChallengeParticipant.filter(
        challenge_id=challenge.id,
        status=ParticipantStatus.APPROVED,
    ).all()

    is_group = challenge.scope == ChallengeScope.GROUP

    if is_group and not _group_goal_achieved(challenge, participants):
        logger.info(
            "그룹 목표 미달성 — 보상 미지급 challenge_id=%d goal_type=%s",
            challenge.id,
            challenge.goal_type,
        )
        return

    source = PointSource.CHALLENGE_GROUP if is_group else PointSource.CHALLENGE_PERIOD

    for participant in participants:
        already_granted = await PointTransaction.filter(
            user_id=participant.user_id,
            source=source,
            source_id=challenge.id,
        ).exists()
        if already_granted:
            continue

        try:
            if is_group:
                await _reward_service.grant_group_completion(
                    user_id=participant.user_id,
                    challenge_id=challenge.id,
                    difficulty_level=challenge.difficulty.value,
                    challenge_title=challenge.title,
                )
            else:
                await _reward_service.grant_period_completion(
                    user_id=participant.user_id,
                    challenge_id=challenge.id,
                    challenge_title=challenge.title,
                )
        except Exception:  # noqa: BLE001
            logger.exception(
                "보상 지급 실패 challenge_id=%d user_id=%d scope=%s",
                challenge.id,
                participant.user_id,
                challenge.scope,
            )


async def complete_expired_challenges(*, dry_run: bool, batch_size: int) -> dict[str, int]:
    """end_date 가 지난 ACTIVE/RECRUITING 챌린지를 COMPLETED 로 일괄 전환한다.

    건별 예외는 격리해(실패가 전체를 막지 않음) 성공/실패 카운트를 집계한다.
    """
    today = date.today()
    started = time.monotonic()

    logger.info(
        "complete_expired_challenges 시작 dry_run=%s batch_size=%d today=%s",
        dry_run,
        batch_size,
        today.isoformat(),
    )

    targets = await Challenge.filter(
        status__in=[ChallengeStatus.ACTIVE, ChallengeStatus.RECRUITING],
        end_date__lt=today,
    ).all()

    total = len(targets)
    logger.info("전환 대상 %d건", total)

    if dry_run:
        for c in targets:
            logger.info("[dry-run] 대상 challenge_id=%d title=%s end_date=%s status=%s", c.id, c.title, c.end_date, c.status)
        elapsed = time.monotonic() - started
        logger.info("[dry-run] 종료 — 대상 %d건, 실제 업데이트 없음, 소요 %.2fs", total, elapsed)
        return {"total": total, "completed": 0, "failed": 0}

    done = 0
    failed = 0
    for batch_start in range(0, total, batch_size):
        batch = targets[batch_start : batch_start + batch_size]
        for challenge in batch:
            challenge_id = challenge.id
            try:
                challenge.status = ChallengeStatus.COMPLETED
                await challenge.save(update_fields=["status"])
                await _grant_completion_rewards(challenge)
                done += 1
            except Exception:  # noqa: BLE001 — 건별 실패 격리
                failed += 1
                logger.exception("전환 실패 challenge_id=%d", challenge_id)
        logger.info(
            "배치 진행 %d/%d (성공 누적 %d, 실패 누적 %d)",
            min(batch_start + batch_size, total),
            total,
            done,
            failed,
        )

    elapsed = time.monotonic() - started
    logger.info(
        "complete_expired_challenges 완료 — 대상 %d건 / 성공 %d건 / 실패 %d건 / 소요 %.2fs",
        total,
        done,
        failed,
        elapsed,
    )
    return {"total": total, "completed": done, "failed": failed}


async def _run(*, dry_run: bool, batch_size: int) -> int:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        result = await complete_expired_challenges(dry_run=dry_run, batch_size=batch_size)
    finally:
        await Tortoise.close_connections()
    return 1 if result["failed"] else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제 status 업데이트를 수행한다. 미지정 시 dry-run(기본 안전값) — 대상만 로깅하고 업데이트하지 않음.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"배치 처리 크기(기본 {DEFAULT_BATCH_SIZE}).",
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
    return asyncio.run(_run(dry_run=not args.apply, batch_size=args.batch_size))


if __name__ == "__main__":
    sys.exit(main())
