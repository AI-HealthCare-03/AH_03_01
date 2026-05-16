from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.pet import (
    GrowthEventRequest,
    InteractionRequest,
    PetCreateRequest,
    PetUpdateRequest,
    PurchaseRequest,
    RewardClaimRequest,
)
from app.models.pet import (
    AttendanceCheck,
    GrowthEventSource,
    InteractionType,
    Inventory,
    Item,
    Pet,
    PointSource,
    PointTransaction,
)
from app.models.users import User
from app.repositories.pet_repository import (
    AttendanceRepository,
    InventoryRepository,
    ItemRepository,
    PetRepository,
    PointTransactionRepository,
    RescueTicketUsageRepository,
)
from app.services.rewards import RewardService

XP_PER_LEVEL = 100
XP_FROM_CHALLENGE_VERIFICATION = 50
XP_FROM_ATTENDANCE = 10
XP_FROM_QUIZ = 30
INTERACTION_POINT_COST = 10
INTERACTION_XP_GAIN = 5
INTERACTION_STAT_DELTA = {
    InteractionType.FEED: {"hunger": 25, "cleanliness": 0, "mood": 5},
    InteractionType.PLAY: {"hunger": -5, "cleanliness": -5, "mood": 25},
    InteractionType.WASH: {"hunger": 0, "cleanliness": 25, "mood": 5},
}


class PetService:
    def __init__(self) -> None:
        self.repo = PetRepository()
        self.point_repo = PointTransactionRepository()
        self.inventory_repo = InventoryRepository()
        self.reward_service = RewardService()

    async def create(self, user: User, data: PetCreateRequest) -> Pet:
        existing = await self.repo.get_by_user(user.id)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 펫을 보유하고 있습니다.")
        async with in_transaction():
            return await self.repo.create(
                user.id,
                data={
                    "name": data.name,
                    "pet_type": data.pet_type,
                    "selected_style": data.selected_style,
                },
            )

    async def get_or_404(self, user: User) -> Pet:
        pet = await self.repo.get_by_user(user.id)
        if pet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="펫이 없습니다. 먼저 생성하세요.")
        return pet

    async def update(self, user: User, data: PetUpdateRequest) -> Pet:
        pet = await self.get_or_404(user)
        async with in_transaction():
            updates: dict[str, Any] = {}
            if data.name is not None:
                updates["name"] = data.name
            if data.selected_style is not None:
                updates["selected_style"] = data.selected_style
            if updates:
                pet = await self.repo.update_instance(pet, updates)
            if data.equipped_item_ids is not None:
                await self.inventory_repo.set_equipped(user.id, data.equipped_item_ids)
        return pet

    async def equipped_items(self, user_id: int) -> list[Inventory]:
        return await self.inventory_repo.list_equipped(user_id)

    async def grant_xp(
        self,
        user_id: int,
        xp: int,
        *,
        source: GrowthEventSource,
        source_id: int | None = None,
    ) -> tuple[Pet, int, int] | None:
        pet = await self.repo.get_by_user(user_id)
        if pet is None or xp <= 0:
            return None
        return await self.repo.add_xp(pet, xp, xp_per_level=XP_PER_LEVEL)

    async def growth_event(self, user: User, data: GrowthEventRequest) -> dict[str, Any]:
        pet = await self.get_or_404(user)
        xp_gain = 0
        consumed_point = 0
        async with in_transaction():
            if data.source == GrowthEventSource.POINT:
                point_amount = data.point_amount or 0
                if point_amount <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="point_amount 는 양수여야 합니다.",
                    )
                balance = await self.point_repo.balance(user.id)
                if balance < point_amount:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="포인트 잔액이 부족합니다.")
                await self.point_repo.spend(
                    user_id=user.id,
                    amount=point_amount,
                    source=PointSource.PET_INTERACTION,
                    description="펫 성장 이벤트(포인트 → XP)",
                )
                xp_gain = point_amount  # 1 P = 1 XP
                consumed_point = point_amount
            elif data.source == GrowthEventSource.CHALLENGE:
                xp_gain = XP_FROM_CHALLENGE_VERIFICATION
            elif data.source == GrowthEventSource.ATTENDANCE:
                xp_gain = XP_FROM_ATTENDANCE
            elif data.source == GrowthEventSource.QUIZ:
                xp_gain = XP_FROM_QUIZ
            else:
                xp_gain = INTERACTION_XP_GAIN

            pet, gained, _ = await self.repo.add_xp(pet, xp_gain, xp_per_level=XP_PER_LEVEL)
        return {
            "pet_id": pet.id,
            "level": pet.level,
            "current_xp": pet.current_xp,
            "xp_gained": gained,
            "consumed_point": consumed_point,
        }

    async def interact(self, user: User, data: InteractionRequest) -> dict[str, Any]:
        pet = await self.get_or_404(user)
        balance = await self.point_repo.balance(user.id)
        if balance < INTERACTION_POINT_COST:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="포인트 잔액이 부족합니다.")
        delta = INTERACTION_STAT_DELTA[data.type]
        async with in_transaction():
            await self.point_repo.spend(
                user_id=user.id,
                amount=INTERACTION_POINT_COST,
                source=PointSource.PET_INTERACTION,
                description=f"펫 상호작용: {data.type.value}",
            )
            pet, gained, _ = await self.repo.add_xp(pet, INTERACTION_XP_GAIN, xp_per_level=XP_PER_LEVEL)
            pet = await self.repo.update_interaction_stats(
                pet,
                hunger_delta=delta["hunger"],
                cleanliness_delta=delta["cleanliness"],
                mood_delta=delta["mood"],
            )
        return {
            "pet_id": pet.id,
            "type": data.type,
            "xp_gained": gained,
            "point_cost": INTERACTION_POINT_COST,
            "level": pet.level,
            "current_xp": pet.current_xp,
            "hunger": pet.hunger,
            "cleanliness": pet.cleanliness,
            "mood": pet.mood,
        }


class StoreService:
    def __init__(self) -> None:
        self.item_repo = ItemRepository()
        self.inventory_repo = InventoryRepository()
        self.point_repo = PointTransactionRepository()

    async def list_items(self, category: str | None) -> list[Item]:
        return await self.item_repo.list_active(category)

    async def purchase(self, user: User, data: PurchaseRequest) -> dict[str, Any]:
        item = await self.item_repo.get(data.item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="아이템을 찾을 수 없습니다.")
        total_cost = item.price * data.quantity
        async with in_transaction():
            balance = await self.point_repo.balance(user.id)
            if balance < total_cost:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="포인트 잔액이 부족합니다.")
            await self.point_repo.spend(
                user_id=user.id,
                amount=total_cost,
                source=PointSource.STORE_PURCHASE,
                source_id=item.id,
                description=f"{item.name} {data.quantity}개 구매",
            )
            inventory = await self.inventory_repo.upsert(user.id, item.id, increment=data.quantity)
            new_balance = await self.point_repo.balance(user.id)
        return {
            "purchase_id": inventory.id,
            "item_id": item.id,
            "quantity": data.quantity,
            "point_spent": total_cost,
            "point_balance": new_balance,
        }


class InventoryService:
    def __init__(self) -> None:
        self.repo = InventoryRepository()

    async def list_items(self, user_id: int, category: str | None) -> list[Inventory]:
        return await self.repo.list_for_user(user_id, category)


class PointService:
    def __init__(self) -> None:
        self.repo = PointTransactionRepository()

    async def balance(self, user_id: int) -> int:
        return await self.repo.balance(user_id)

    async def list_transactions(
        self,
        user_id: int,
        *,
        tx_type: str | None,
        source: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[PointTransaction]:
        # 최대 1년 범위 제한 (정책)
        if date_from and date_to and (date_to - date_from).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="조회 범위는 최대 1년입니다.",
            )
        return await self.repo.list_for_user(
            user_id,
            tx_type=tx_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )


class AttendanceService:
    def __init__(self) -> None:
        self.repo = AttendanceRepository()
        self.point_repo = PointTransactionRepository()
        self.reward_service = RewardService()
        self.pet_service = PetService()

    async def list_month(self, user_id: int, year: int, month: int) -> tuple[list[AttendanceCheck], int]:
        records = await self.repo.list_for_month(user_id, year, month)
        latest = await self.repo.latest_before(user_id, date.today() + timedelta(days=1))
        current_streak = latest.streak_days if latest and latest.check_date == date.today() else 0
        return records, current_streak

    async def check_in(self, user: User) -> dict[str, Any]:
        today = datetime.now(config.TIMEZONE).date()
        existing = await self.repo.get_for_date(user.id, today)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="오늘 이미 출석했습니다.")
        previous = await self.repo.latest_before(user.id, today)
        streak = 1
        if previous is not None and previous.check_date == today - timedelta(days=1):
            streak = previous.streak_days + 1

        async with in_transaction():
            attendance = await self.repo.create(
                data={
                    "user_id": user.id,
                    "check_date": today,
                    "streak_days": streak,
                    "daily_point_amount": RewardService.ATTENDANCE_DAILY,
                }
            )
            daily_reward = await self.reward_service.grant_attendance_daily(
                user_id=user.id, attendance_id=attendance.id
            )
            tx_ids = [daily_reward.transaction.id]
            bonus_point = 0
            if streak in RewardService.ATTENDANCE_BONUS_THRESHOLDS:
                bonus = await self.reward_service.grant_attendance_bonus(
                    user_id=user.id, attendance_id=attendance.id, streak_days=streak
                )
                bonus_point = bonus.amount
                tx_ids.append(bonus.transaction.id)
                attendance.bonus_awarded = True
                attendance.bonus_point_amount = bonus_point
                await attendance.save(update_fields=["bonus_awarded", "bonus_point_amount"])
            # 출석으로 펫에 XP 가산 (펫이 없으면 무시)
            await self.pet_service.grant_xp(
                user.id,
                XP_FROM_ATTENDANCE,
                source=GrowthEventSource.ATTENDANCE,
                source_id=attendance.id,
            )
        return {
            "check_date": today,
            "streak_days": streak,
            "reward_point": RewardService.ATTENDANCE_DAILY,
            "bonus_point": bonus_point,
            "transaction_ids": tx_ids,
        }


class RewardClaimService:
    """챌린지 보상 명시 클레임 API. 자동 지급되지 않은 보상을 사용자가 요청해 받을 때 사용."""

    def __init__(self) -> None:
        self.reward_service = RewardService()
        self.point_repo = PointTransactionRepository()

    async def claim(
        self,
        user: User,
        reward_type: str,
        data: RewardClaimRequest,
    ) -> dict[str, Any]:
        async with in_transaction():
            if reward_type == "daily":
                if data.verification_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="daily 보상은 verification_id 가 필요합니다.",
                    )
                result = await self.reward_service.grant_daily(
                    user_id=user.id,
                    challenge_id=data.challenge_id,
                    verification_id=data.verification_id,
                )
            elif reward_type == "period":
                result = await self.reward_service.grant_period_completion(
                    user_id=user.id, challenge_id=data.challenge_id
                )
            elif reward_type == "group":
                if not data.difficulty_level:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="group 보상은 difficulty_level 이 필요합니다.",
                    )
                result = await self.reward_service.grant_group_completion(
                    user_id=user.id,
                    challenge_id=data.challenge_id,
                    difficulty_level=data.difficulty_level,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="rewardType 은 daily|period|group 입니다.",
                )
            new_balance = await self.point_repo.balance(user.id)
        return {
            "transaction_id": result.transaction.id,
            "reward_type": result.reward_type,
            "point_amount": result.amount,
            "point_balance": new_balance,
        }


class RescueTicketService:
    """SHIELD 인증 처리 시 사용. 보유 티켓 1장 차감 + 사용 기록 생성."""

    def __init__(self) -> None:
        self.inventory_repo = InventoryRepository()
        self.usage_repo = RescueTicketUsageRepository()

    async def consume(self, user_id: int, challenge_id: int, used_date: date) -> Inventory:
        ticket = await self.inventory_repo.find_active_rescue_ticket(user_id)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="실패 방지권이 없습니다.")
        async with in_transaction():
            await self.inventory_repo.decrement(ticket, 1)
            await self.usage_repo.create(
                data={
                    "user_id": user_id,
                    "challenge_id": challenge_id,
                    "inventory_id": ticket.id,
                    "used_date": used_date,
                }
            )
        return ticket


def xp_to_next_level(current_xp: int) -> int:
    return max(0, XP_PER_LEVEL - current_xp)


async def equipped_items_payload(user_id: int) -> list[dict[str, Any]]:
    from app.repositories.pet_repository import InventoryRepository as _InvRepo  # noqa: PLC0415

    items = await _InvRepo().list_equipped(user_id)
    payload: list[dict[str, Any]] = []
    for inv in items:
        await inv.fetch_related("item")
        payload.append(
            {
                "inventory_id": inv.id,
                "item_id": inv.item_id,
                "category": inv.item.category,
                "name": inv.item.name,
            }
        )
    return payload
