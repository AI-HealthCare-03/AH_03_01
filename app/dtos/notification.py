from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notifications import NotificationType


class NotificationResponse(BaseModel):
    id: int
    notification_type: NotificationType
    target_type: str
    target_id: int
    message: str
    is_read: bool
    created_at: datetime
    actor_nickname: str | None = None

    model_config = ConfigDict(from_attributes=True)
