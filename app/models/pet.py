from enum import StrEnum
from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.challenge import Challenge
    from app.models.users import User


class PetType(StrEnum):
    DOG = "DOG"
    CAT = "CAT"
    PLANT = "PLANT"


class ItemCategory(StrEnum):
    BACKGROUND = "BACKGROUND"
    FURNITURE = "FURNITURE"
    PET = "PET"
    TICKET = "TICKET"
    MEDICINE = "MEDICINE"
    DECORATION = "DECORATION"
    FOOD_ANIMAL = "FOOD_ANIMAL"
    FOOD_ANIMAL_PREMIUM = "FOOD_ANIMAL_PREMIUM"
    SNACK_ANIMAL = "SNACK_ANIMAL"
    FERTILIZER_PLANT = "FERTILIZER_PLANT"
    FERTILIZER_PLANT_PREMIUM = "FERTILIZER_PLANT_PREMIUM"
    SUPPLEMENT_PLANT = "SUPPLEMENT_PLANT"
    WATER = "WATER"


class PointTransactionType(StrEnum):
    EARN = "EARN"
    SPEND = "SPEND"


class PointSource(StrEnum):
    CHALLENGE_DAILY = "CHALLENGE_DAILY"
    CHALLENGE_PERIOD = "CHALLENGE_PERIOD"
    CHALLENGE_GROUP = "CHALLENGE_GROUP"
    CHALLENGE_WEEKLY_RANK = "CHALLENGE_WEEKLY_RANK"
    ATTENDANCE_DAILY = "ATTENDANCE_DAILY"
    ATTENDANCE_BONUS = "ATTENDANCE_BONUS"
    QUIZ = "QUIZ"
    STORE_PURCHASE = "STORE_PURCHASE"
    PET_INTERACTION = "PET_INTERACTION"
    REFUND = "REFUND"
    ETC = "ETC"


class GrowthEventSource(StrEnum):
    CHALLENGE = "CHALLENGE"
    ATTENDANCE = "ATTENDANCE"
    QUIZ = "QUIZ"
    INTERACTION = "INTERACTION"
    POINT = "POINT"


class InteractionType(StrEnum):
    FEED = "FEED"
    PLAY = "PLAY"
    WASH = "WASH"


class Pet(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.OneToOneRelation["User"] = fields.OneToOneField(
        "models.User", related_name="pet", on_delete=fields.CASCADE
    )
    name = fields.CharField(max_length=20)
    pet_type = fields.CharEnumField(enum_type=PetType, default=PetType.DOG)
    selected_style = fields.CharField(max_length=40, null=True)
    level = fields.IntField(default=1)
    current_xp = fields.IntField(default=0)
    total_xp = fields.IntField(default=0)
    hunger = fields.IntField(default=80)
    cleanliness = fields.IntField(default=80)
    mood = fields.IntField(default=80)
    intimacy = fields.IntField(default=0)
    sick = fields.BooleanField(default=False)
    equipped_background_id = fields.BigIntField(null=True)
    equipped_furniture_ids: list[int] = fields.JSONField(default=list)  # type: ignore[assignment]
    equipped_decoration_ids: list[int] = fields.JSONField(default=list)  # type: ignore[assignment]
    last_decay_at = fields.DatetimeField(null=True)
    last_interacted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "pets"


class Item(models.Model):
    id = fields.BigIntField(primary_key=True)
    category = fields.CharEnumField(enum_type=ItemCategory)
    name = fields.CharField(max_length=80)
    description = fields.TextField(null=True)
    price = fields.IntField(default=0)
    thumbnail_file_id = fields.BigIntField(null=True)
    item_metadata: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    species_lock = fields.CharEnumField(enum_type=PetType, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "items"
        indexes = [("category", "is_active")]


class Inventory(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="inventory_items", on_delete=fields.CASCADE
    )
    user_id: int
    item: fields.ForeignKeyRelation["Item"] = fields.ForeignKeyField(
        # RESTRICT: 보유 중인 아이템은 삭제 불가(DB가 거부) → 구매 자산 보호.
        # 아이템 은퇴는 삭제가 아니라 is_active=FALSE 로만 처리한다.
        "models.Item",
        related_name="inventory_entries",
        on_delete=fields.RESTRICT,
    )
    item_id: int
    quantity = fields.IntField(default=1)
    is_equipped = fields.BooleanField(default=False)
    acquired_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "inventories"
        unique_together = (("user", "item"),)
        indexes = [("user_id", "is_equipped")]


class PointTransaction(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="point_transactions", on_delete=fields.CASCADE
    )
    user_id: int
    type = fields.CharEnumField(enum_type=PointTransactionType)
    amount = fields.IntField()
    balance_after = fields.IntField(default=0)
    source = fields.CharEnumField(enum_type=PointSource)
    source_id = fields.BigIntField(null=True)
    description = fields.CharField(max_length=200, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "point_transactions"
        indexes = [("user_id", "created_at"), ("user_id", "source")]


class AttendanceCheck(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="attendance_checks", on_delete=fields.CASCADE
    )
    user_id: int
    check_date = fields.DateField()
    streak_days = fields.IntField(default=1)
    bonus_awarded = fields.BooleanField(default=False)
    daily_point_amount = fields.IntField(default=0)
    bonus_point_amount = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "attendance_checks"
        unique_together = (("user", "check_date"),)
        indexes = [("user_id", "check_date")]


class RescueTicketUsage(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="rescue_ticket_usages", on_delete=fields.CASCADE
    )
    user_id: int
    challenge: fields.ForeignKeyRelation["Challenge"] = fields.ForeignKeyField(
        "models.Challenge", related_name="rescue_ticket_usages", on_delete=fields.CASCADE
    )
    challenge_id: int
    inventory: fields.ForeignKeyRelation["Inventory"] = fields.ForeignKeyField(
        "models.Inventory", related_name="rescue_usages", on_delete=fields.CASCADE
    )
    inventory_id: int
    used_date = fields.DateField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "rescue_ticket_usages"
        indexes = [("user_id", "used_date"), ("challenge_id",)]
