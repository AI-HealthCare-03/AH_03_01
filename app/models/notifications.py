from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class NotificationType(StrEnum):
    COMMENT = "COMMENT"
    REPLY = "REPLY"
    LIKE = "LIKE"
    CHALLENGE_KICK = "CHALLENGE_KICK"
    CHALLENGE_INVITE = "CHALLENGE_INVITE"
    RISK_CHANGE = "RISK_CHANGE"


class Notification(models.Model):
    id = fields.BigIntField(primary_key=True)
    recipient: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="notifications", on_delete=fields.CASCADE
    )
    actor: fields.ForeignKeyNullableRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="sent_notifications", on_delete=fields.SET_NULL, null=True
    )
    notification_type = fields.CharEnumField(NotificationType, max_length=20)
    target_type = fields.CharField(max_length=20)  # POST, COMMENT, VERIFICATION
    target_id = fields.BigIntField()
    message = fields.CharField(max_length=200)
    is_read = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notifications"
        ordering = ["-created_at"]
