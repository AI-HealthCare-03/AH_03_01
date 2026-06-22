from datetime import datetime, time

from pydantic import BaseModel, Field


class MedicationReminderCreate(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=100)
    reminder_time: time  # "HH:MM" or "HH:MM:SS"


class MedicationReminderUpdate(BaseModel):
    medicine_name: str | None = Field(None, min_length=1, max_length=100)
    reminder_time: time | None = None
    is_active: bool | None = None


class MedicationReminderResponse(BaseModel):
    id: int
    medicine_name: str
    reminder_time: time
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FcmTokenRequest(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=256)
