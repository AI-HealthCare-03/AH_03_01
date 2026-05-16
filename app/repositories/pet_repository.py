from datetime import date, datetime
from typing import Any

from app.core import config
from app.models.pet import (
    AttendanceCheck,
    Inventory,
    Item,
    ItemCategory,
    Pet,
    PointSource,
    PointTransaction,
    PointTransactionType,
    RescueTicketUsage,
)


class PetRepository:
    def __init__(self) -> None:
        self._model = Pet

    async def get_by_user(self, user_id: int) -> Pet | None:
        return await self._model.get_or_none(user_id=user_id)

    async def create(self, user_id: int, data: dict[str, Any]) -> Pet:
        return await self._model.create(user_id=user_id, **data)

    async def update_instance(self, pet: Pet, data: dict[str, Any]) -> Pet:
        update_fields = []
        for key, value in data.items():
            if value is not None:
                setattr(pet, key, value)
                update_fields.append(key)
        if update_fields:
            await pet.save(update_fields=update_fields)
        return pet

    async def add_xp(self, pet: Pet, xp_gain: int, *, xp_per_level: int = 100) -> tuple[Pet, int, int]:
        pet.current_xp += xp_gain
        pet.total_xp += xp_gain
        level_ups = 0
        while pet.current_xp >= xp_per_level:
            pet.current_xp -= xp_per_level
            pet.level += 1
            level_ups += 1
        await pet.save(update_fields=["current_xp", "total_xp", "level"])
        return pet, xp_gain, level_ups

    async def update_interaction_stats(
        self,
        pet: Pet,
        *,
        hunger_delta: int,
        cleanliness_delta: int,
        mood_delta: int,
    ) -> Pet:
        pet.hunger = max(0, min(100, pet.hunger + hunger_delta))
        pet.cleanliness = max(0, min(100, pet.cleanliness + cleanliness_delta))
        pet.mood = max(0, min(100, pet.mood + mood_delta))
        pet.last_interacted_at = datetime.now(config.TIMEZONE)
        await pet.save(update_fields=["hunger", "cleanliness", "mood", "last_interacted_at"])
        return pet


class ItemRepository:
    def __init__(self) -> None:
        self._model = Item

    async def list_active(self, category: str | None = None) -> list[Item]:
        qs = self._model.filter(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return list(await qs.order_by("category", "price", "id"))

    async def get(self, item_id: int) -> Item | None:
        return await self._model.get_or_none(id=item_id, is_active=True)


class InventoryRepository:
    def __init__(self) -> None:
        self._model = Inventory

    async def list_for_user(
        self,
        user_id: int,
        category: str | None = None,
    ) -> list[Inventory]:
        qs = self._model.filter(user_id=user_id).prefetch_related("item")
        if category:
            qs = qs.filter(item__category=category)
        return list(await qs.order_by("-acquired_at"))

    async def get_or_none(self, user_id: int, item_id: int) -> Inventory | None:
        return await self._model.get_or_none(user_id=user_id, item_id=item_id)

    async def upsert(self, user_id: int, item_id: int, *, increment: int = 1) -> Inventory:
        existing = await self._model.get_or_none(user_id=user_id, item_id=item_id)
        if existing is None:
            return await self._model.create(user_id=user_id, item_id=item_id, quantity=increment)
        existing.quantity += increment
        await existing.save(update_fields=["quantity"])
        return existing

    async def decrement(self, inventory: Inventory, amount: int = 1) -> Inventory:
        inventory.quantity = max(0, inventory.quantity - amount)
        await inventory.save(update_fields=["quantity"])
        return inventory

    async def set_equipped(self, user_id: int, item_ids: list[int]) -> None:
        # 전체를 false 로 초기화 후 명시된 것만 true 로 설정
        await self._model.filter(user_id=user_id).update(is_equipped=False)
        if item_ids:
            await self._model.filter(user_id=user_id, item_id__in=item_ids).update(is_equipped=True)

    async def list_equipped(self, user_id: int) -> list[Inventory]:
        return list(await self._model.filter(user_id=user_id, is_equipped=True).prefetch_related("item"))

    async def find_active_rescue_ticket(self, user_id: int) -> Inventory | None:
        return await (
            self._model.filter(user_id=user_id, item__category=ItemCategory.TICKET, quantity__gt=0)
            .prefetch_related("item")
            .first()
        )


class PointTransactionRepository:
    def __init__(self) -> None:
        self._model = PointTransaction

    async def balance(self, user_id: int) -> int:
        # balance_after 컬럼에 누적 잔액을 저장하므로 마지막 행만 보면 된다.
        latest = await self._model.filter(user_id=user_id).order_by("-id").first()
        return int(latest.balance_after) if latest else 0

    async def grant(
        self,
        *,
        user_id: int,
        amount: int,
        source: PointSource,
        source_id: int | None = None,
        description: str | None = None,
    ) -> PointTransaction:
        if amount <= 0:
            raise ValueError("grant amount must be positive")
        balance = await self.balance(user_id) + amount
        return await self._model.create(
            user_id=user_id,
            type=PointTransactionType.EARN,
            amount=amount,
            balance_after=balance,
            source=source,
            source_id=source_id,
            description=description,
        )

    async def spend(
        self,
        *,
        user_id: int,
        amount: int,
        source: PointSource,
        source_id: int | None = None,
        description: str | None = None,
    ) -> PointTransaction:
        if amount <= 0:
            raise ValueError("spend amount must be positive")
        balance = await self.balance(user_id) - amount
        return await self._model.create(
            user_id=user_id,
            type=PointTransactionType.SPEND,
            amount=amount,
            balance_after=balance,
            source=source,
            source_id=source_id,
            description=description,
        )

    async def list_for_user(
        self,
        user_id: int,
        *,
        tx_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PointTransaction]:
        qs = self._model.filter(user_id=user_id)
        if tx_type:
            qs = qs.filter(type=tx_type)
        if source:
            qs = qs.filter(source=source)
        if date_from:
            qs = qs.filter(created_at__gte=datetime.combine(date_from, datetime.min.time()))
        if date_to:
            qs = qs.filter(created_at__lte=datetime.combine(date_to, datetime.max.time()))
        return list(await qs.order_by("-created_at"))


class AttendanceRepository:
    def __init__(self) -> None:
        self._model = AttendanceCheck

    async def get_for_date(self, user_id: int, check_date: date) -> AttendanceCheck | None:
        return await self._model.get_or_none(user_id=user_id, check_date=check_date)

    async def latest_before(self, user_id: int, check_date: date) -> AttendanceCheck | None:
        return await self._model.filter(user_id=user_id, check_date__lt=check_date).order_by("-check_date").first()

    async def list_for_month(self, user_id: int, year: int, month: int) -> list[AttendanceCheck]:
        from calendar import monthrange

        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return list(
            await self._model.filter(user_id=user_id, check_date__gte=start, check_date__lte=end).order_by("check_date")
        )

    async def create(self, data: dict[str, Any]) -> AttendanceCheck:
        return await self._model.create(**data)


class RescueTicketUsageRepository:
    def __init__(self) -> None:
        self._model = RescueTicketUsage

    async def create(self, data: dict[str, Any]) -> RescueTicketUsage:
        return await self._model.create(**data)
