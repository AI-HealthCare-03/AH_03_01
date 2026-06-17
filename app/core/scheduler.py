import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core import config

_logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _send_medication_reminders() -> None:
    now = datetime.now(tz=config.TIMEZONE)
    from app.repositories.medication_reminder_repository import MedicationReminderRepository
    from app.services.fcm_service import send_medication_push

    repo = MedicationReminderRepository()
    reminders = await repo.get_active_by_time(now.time())
    if not reminders:
        return

    tasks = []
    for reminder in reminders:
        token = reminder.user.fcm_token
        if token:
            tasks.append(send_medication_push(token, reminder.medicine_name))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            _logger.warning("복약 알림 발송 실패: %d건/%d건", len(failures), len(tasks))
        else:
            _logger.info("복약 알림 발송 완료: %d건", len(tasks))


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=str(config.TIMEZONE))
        _scheduler.add_job(
            _send_medication_reminders,
            trigger="cron",
            minute="*",  # 매 분 실행
            id="medication_reminder",
            replace_existing=True,
            misfire_grace_time=30,
        )
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        _logger.info("APScheduler 시작 (복약 알림)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _logger.info("APScheduler 종료")
