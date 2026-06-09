from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.security import get_request_user
from app.dtos.notification import NotificationResponse
from app.models.notifications import Notification
from app.models.users import User
from app.repositories.notification_repository import NotificationRepository

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


def _build(n: Notification) -> NotificationResponse:
    actor_nickname = n.actor.nickname if n.actor_id is not None else None
    return NotificationResponse(
        id=n.id,
        notification_type=n.notification_type,
        target_type=n.target_type,
        target_id=n.target_id,
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at,
        actor_nickname=actor_nickname,
    )


@notifications_router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    since: datetime | None = Query(None),  # noqa: B008
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> list[NotificationResponse]:
    notifs = await NotificationRepository().list(current_user.id, since)
    return [_build(n) for n in notifs]


@notifications_router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> None:
    updated = await NotificationRepository().mark_read(notification_id, current_user.id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")


@notifications_router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(current_user: User = Depends(get_request_user)) -> None:  # noqa: B008
    await NotificationRepository().mark_all_read(current_user.id)
