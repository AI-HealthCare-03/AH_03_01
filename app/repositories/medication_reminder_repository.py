from datetime import time
from uuid import UUID

from app.models.medication_reminder import MedicationReminder


class MedicationReminderRepository:
    async def list_by_user(self, user_id: UUID) -> list[MedicationReminder]:
        return await MedicationReminder.filter(user_id=user_id).all()

    async def get(self, reminder_id: int, user_id: UUID) -> MedicationReminder | None:
        return await MedicationReminder.get_or_none(id=reminder_id, user_id=user_id)

    async def create(self, user_id: UUID, medicine_name: str, reminder_time: time) -> MedicationReminder:
        return await MedicationReminder.create(
            user_id=user_id,
            medicine_name=medicine_name,
            reminder_time=reminder_time,
        )

    async def update(self, reminder: MedicationReminder, **kwargs: object) -> MedicationReminder:
        for key, value in kwargs.items():
            if value is not None:
                setattr(reminder, key, value)
        await reminder.save()
        return reminder

    async def delete(self, reminder: MedicationReminder) -> None:
        await reminder.delete()

    async def get_active_by_time(self, reminder_time: time) -> list[MedicationReminder]:
        """정각 매칭: HH:MM 기준으로 활성화된 알림 조회 (select_related로 fcm_token 포함)."""
        return await MedicationReminder.filter(
            is_active=True,
            reminder_time__hour=reminder_time.hour,
            reminder_time__minute=reminder_time.minute,
        ).select_related("user")
