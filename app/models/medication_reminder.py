from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class MedicationReminder(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="medication_reminders", on_delete=fields.CASCADE
    )
    medicine_name = fields.CharField(max_length=100)
    reminder_time = fields.TimeField()  # HH:MM:SS
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication_reminders"
        ordering = ["reminder_time"]
