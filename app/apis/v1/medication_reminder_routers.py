from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.security import get_request_user
from app.dtos.medication_reminder import (
    FcmTokenRequest,
    MedicationReminderCreate,
    MedicationReminderResponse,
    MedicationReminderUpdate,
)
from app.models.users import User
from app.repositories.medication_reminder_repository import MedicationReminderRepository

medication_reminders_router = APIRouter(prefix="/medication-reminders", tags=["medication-reminders"])
fcm_router = APIRouter(prefix="/users", tags=["users"])


@fcm_router.post("/fcm-token", status_code=status.HTTP_204_NO_CONTENT)
async def register_fcm_token(
    body: FcmTokenRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> None:
    current_user.fcm_token = body.fcm_token
    await current_user.save(update_fields=["fcm_token"])


@medication_reminders_router.get("", response_model=list[MedicationReminderResponse])
async def list_reminders(
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> list[MedicationReminderResponse]:
    reminders = await MedicationReminderRepository().list_by_user(current_user.id)
    return [MedicationReminderResponse.model_validate(r) for r in reminders]


@medication_reminders_router.post("", response_model=MedicationReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: MedicationReminderCreate,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> MedicationReminderResponse:
    reminder = await MedicationReminderRepository().create(
        user_id=current_user.id,
        medicine_name=body.medicine_name,
        reminder_time=body.reminder_time,
    )
    return MedicationReminderResponse.model_validate(reminder)


@medication_reminders_router.patch("/{reminder_id}", response_model=MedicationReminderResponse)
async def update_reminder(
    reminder_id: int,
    body: MedicationReminderUpdate,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> MedicationReminderResponse:
    repo = MedicationReminderRepository()
    reminder = await repo.get(reminder_id, current_user.id)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")
    updates = body.model_dump(exclude_none=True)
    reminder = await repo.update(reminder, **updates)
    return MedicationReminderResponse.model_validate(reminder)


@medication_reminders_router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> None:
    repo = MedicationReminderRepository()
    reminder = await repo.get(reminder_id, current_user.id)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")
    await repo.delete(reminder)
