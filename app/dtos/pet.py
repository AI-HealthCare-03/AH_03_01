from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel
from app.models.pet import (
    GrowthEventSource,
    InteractionType,
    ItemCategory,
    PetType,
    PointSource,
    PointTransactionType,
)

# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------


class PetCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=20)]
    pet_type: PetType = PetType.DOG
    selected_style: Annotated[str | None, Field(None, max_length=40)] = None


class PetUpdateRequest(BaseModel):
    name: Annotated[str | None, Field(None, min_length=1, max_length=20)] = None
    selected_style: Annotated[str | None, Field(None, max_length=40)] = None
    equipped_item_ids: list[int] | None = None


class EquippedItem(BaseModel):
    inventory_id: int
    item_id: int
    category: ItemCategory
    name: str


class PetResponse(BaseSerializerModel):
    id: int
    name: str
    pet_type: PetType
    selected_style: str | None
    level: int
    current_xp: int
    total_xp: int
    hunger: int
    cleanliness: int
    mood: int
    intimacy: int = 0
    sick: bool = False
    equipped_background_id: int | None = None
    equipped_furniture_ids: list[int] = []
    equipped_decoration_ids: list[int] = []
    last_interacted_at: datetime | None
    created_at: datetime


class EquippedBackgroundMeta(BaseModel):
    id: int
    name: str
    gradient: str | None = None
    image: str | None = None  # main|sunset|star|beach (이미지 배경 키)


class EquippedItemMeta(BaseModel):
    id: int
    name: str
    emoji: str | None = None
    slot: str | None = None
    placement: str | None = None  # head|paws|stage_top|stage_bottom
    asset: str | None = None  # 이미지 경로 (/pets/items/*.png)
    variant: str | None = None  # ribbon|flower|ball|butterfly


class PetDetailResponse(PetResponse):
    equipped_items: list[EquippedItem] = []
    equipped_background: EquippedBackgroundMeta | None = None
    equipped_furniture: list[EquippedItemMeta] = []
    equipped_decoration: list[EquippedItemMeta] = []
    xp_to_next_level: int = 100


class GrowthEventRequest(BaseModel):
    source: GrowthEventSource = GrowthEventSource.POINT
    point_amount: Annotated[int | None, Field(None, ge=0)] = None
    transaction_id: int | None = None


class GrowthEventResponse(BaseModel):
    pet_id: int
    level: int
    current_xp: int
    xp_gained: int
    consumed_point: int


class InteractionRequest(BaseModel):
    type: InteractionType


class InteractionResponse(BaseModel):
    pet_id: int
    type: InteractionType
    xp_gained: int
    point_cost: int
    level: int
    current_xp: int
    hunger: int
    cleanliness: int
    mood: int


# ---------------------------------------------------------------------------
# Store / Inventory / Points / Attendance / Reward claim
# ---------------------------------------------------------------------------


class ItemResponse(BaseSerializerModel):
    id: int
    category: ItemCategory
    name: str
    description: str | None
    price: int
    thumbnail_file_id: int | None
    item_metadata: dict[str, Any]
    species_lock: PetType | None = None


class StoreItemsResponse(BaseModel):
    items: list[ItemResponse]


class PurchaseRequest(BaseModel):
    item_id: int
    quantity: Annotated[int, Field(ge=1, le=99)] = 1


class PurchaseResponse(BaseModel):
    purchase_id: int
    item_id: int
    quantity: int
    point_spent: int
    point_balance: int


class InventoryItemResponse(BaseSerializerModel):
    id: int
    item_id: int
    category: ItemCategory
    name: str
    quantity: int
    is_equipped: bool
    acquired_at: datetime
    asset: str | None = None  # 아이템 썸네일 이미지 경로


class InventoryListResponse(BaseModel):
    items: list[InventoryItemResponse]


class InventoryUseResponse(BaseModel):
    inventory_id: int
    item_id: int
    category: ItemCategory
    remaining_quantity: int
    pet_id: int | None = None
    sick: bool | None = None
    hunger: int | None = None
    cleanliness: int | None = None
    mood: int | None = None
    intimacy: int | None = None
    xp_gained: int | None = None
    level: int | None = None
    message: str


class PointTransactionResponse(BaseSerializerModel):
    id: int
    type: PointTransactionType
    amount: int
    balance_after: int
    source: PointSource
    source_id: int | None
    description: str | None
    created_at: datetime


class PointTransactionListResponse(BaseModel):
    balance: int
    transactions: list[PointTransactionResponse]


class AttendanceMonthResponse(BaseModel):
    month: str
    checked_dates: list[date]
    current_streak: int
    next_bonus_at: int | None


class AttendanceCheckResponse(BaseModel):
    check_date: date
    streak_days: int
    reward_point: int
    bonus_point: int
    transaction_ids: list[int]
