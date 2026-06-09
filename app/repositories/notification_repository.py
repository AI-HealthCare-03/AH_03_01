from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.notifications import Notification, NotificationType


class NotificationRepository:
    async def list(self, recipient_id: UUID, since: datetime | None = None) -> list[Notification]:
        qs = Notification.filter(recipient_id=recipient_id).prefetch_related("actor")
        if since:
            qs = qs.filter(created_at__gt=since)
        return list(await qs.order_by("-created_at").limit(50))

    async def mark_read(self, notification_id: int, recipient_id: UUID) -> bool:
        count = await Notification.filter(id=notification_id, recipient_id=recipient_id).update(is_read=True)
        return count > 0

    async def mark_all_read(self, recipient_id: UUID) -> None:
        await Notification.filter(recipient_id=recipient_id, is_read=False).update(is_read=True)

    async def create(
        self,
        recipient_id: UUID,
        actor_id: UUID | None,
        notification_type: NotificationType,
        target_type: str,
        target_id: int,
        message: str,
    ) -> Notification:
        return await Notification.create(
            recipient_id=recipient_id,
            actor_id=actor_id,
            notification_type=notification_type,
            target_type=target_type,
            target_id=target_id,
            message=message,
        )
