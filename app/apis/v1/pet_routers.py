from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.pet import (
    AttendanceCheckResponse,
    AttendanceMonthResponse,
    GrowthEventRequest,
    GrowthEventResponse,
    InteractionRequest,
    InteractionResponse,
    InventoryItemResponse,
    InventoryListResponse,
    InventoryUseResponse,
    ItemResponse,
    PetCreateRequest,
    PetDetailResponse,
    PetResponse,
    PetUpdateRequest,
    PointTransactionListResponse,
    PointTransactionResponse,
    PurchaseRequest,
    PurchaseResponse,

    StoreItemsResponse,
)
from app.models.pet import ItemCategory, PointSource, PointTransactionType
from app.models.users import User
from app.services.pet import (
    AttendanceService,
    InventoryService,
    PetService,
    PointService,

    StoreService,
    equipped_items_payload,
    equipped_slots_payload,
    xp_to_next_level,
)

pets_router = APIRouter(prefix="/pets", tags=["pets"])
store_router = APIRouter(prefix="/store", tags=["store"])
inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])
points_router = APIRouter(prefix="/points", tags=["points"])
attendance_router = APIRouter(prefix="/attendance-checks", tags=["attendance"])
rewards_router = APIRouter(prefix="/rewards", tags=["rewards"])


# ---------------------------------------------------------------------------
# /pets
# ---------------------------------------------------------------------------


@pets_router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
async def create_pet(
    body: PetCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[PetService, Depends(PetService)],
) -> Response:
    pet = await service.create(user, body)
    return Response(PetResponse.model_validate(pet).model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@pets_router.get("/me", response_model=PetDetailResponse, status_code=status.HTTP_200_OK)
async def get_my_pet(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[PetService, Depends(PetService)],
) -> Response:
    pet = await service.get_or_404(user)
    pet = await service.decay_if_needed(pet)
    payload = PetDetailResponse.model_validate(pet).model_dump(mode="json")
    payload["equipped_items"] = await equipped_items_payload(user.id)
    payload.update(await equipped_slots_payload(pet))
    payload["xp_to_next_level"] = xp_to_next_level(pet.current_xp)
    return Response(payload, status_code=status.HTTP_200_OK)


@pets_router.patch("/me", response_model=PetDetailResponse, status_code=status.HTTP_200_OK)
async def update_my_pet(
    body: PetUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[PetService, Depends(PetService)],
) -> Response:
    pet = await service.update(user, body)
    payload = PetDetailResponse.model_validate(pet).model_dump(mode="json")
    payload["equipped_items"] = await equipped_items_payload(user.id)
    payload.update(await equipped_slots_payload(pet))
    payload["xp_to_next_level"] = xp_to_next_level(pet.current_xp)
    return Response(payload, status_code=status.HTTP_200_OK)


@pets_router.post(
    "/me/growth-events",
    response_model=GrowthEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grow_pet(
    body: GrowthEventRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[PetService, Depends(PetService)],
) -> Response:
    payload = await service.growth_event(user, body)
    return Response(payload, status_code=status.HTTP_201_CREATED)


@pets_router.post(
    "/me/interactions",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def interact_with_pet(
    body: InteractionRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[PetService, Depends(PetService)],
) -> Response:
    payload = await service.interact(user, body)
    return Response(payload, status_code=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# /store
# ---------------------------------------------------------------------------


@store_router.get("/items", response_model=StoreItemsResponse, status_code=status.HTTP_200_OK)
async def list_store_items(
    _: Annotated[User, Depends(get_request_user)],
    service: Annotated[StoreService, Depends(StoreService)],
    category: Annotated[ItemCategory | None, Query()] = None,
) -> Response:
    items = await service.list_items(category.value if category else None)
    payload = StoreItemsResponse(items=[ItemResponse.model_validate(i) for i in items])
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@store_router.post("/purchases", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_item(
    body: PurchaseRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[StoreService, Depends(StoreService)],
) -> Response:
    payload = await service.purchase(user, body)
    return Response(payload, status_code=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# /inventory
# ---------------------------------------------------------------------------


@inventory_router.post(
    "/{inventory_id}/use",
    response_model=InventoryUseResponse,
    status_code=status.HTTP_200_OK,
)
async def use_inventory_item(
    inventory_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[InventoryService, Depends(InventoryService)],
) -> Response:
    payload = await service.use(user, inventory_id)
    return Response(payload, status_code=status.HTTP_200_OK)


@inventory_router.get("", response_model=InventoryListResponse, status_code=status.HTTP_200_OK)
async def list_inventory(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[InventoryService, Depends(InventoryService)],
    category: Annotated[ItemCategory | None, Query()] = None,
) -> Response:
    items = await service.list_items(user.id, category.value if category else None)
    payload = InventoryListResponse(
        items=[
            InventoryItemResponse(
                id=inv.id,
                item_id=inv.item_id,
                category=inv.item.category,
                name=inv.item.name,
                quantity=inv.quantity,
                is_equipped=inv.is_equipped,
                acquired_at=inv.acquired_at,
                asset=(inv.item.item_metadata or {}).get("asset"),
            )
            for inv in items
        ]
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# /points
# ---------------------------------------------------------------------------


@points_router.get(
    "/transactions",
    response_model=PointTransactionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_point_transactions(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[PointService, Depends(PointService)],
    tx_type: Annotated[PointTransactionType | None, Query(alias="type")] = None,
    source: Annotated[PointSource | None, Query()] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> Response:
    txs = await service.list_transactions(
        user.id,
        tx_type=tx_type.value if tx_type else None,
        source=source.value if source else None,
        date_from=date_from,
        date_to=date_to,
    )
    balance = await service.balance(user.id)
    payload = PointTransactionListResponse(
        balance=balance,
        transactions=[PointTransactionResponse.model_validate(t) for t in txs],
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# /attendance-checks
# ---------------------------------------------------------------------------


@attendance_router.get(
    "",
    response_model=AttendanceMonthResponse,
    status_code=status.HTTP_200_OK,
)
async def get_attendance_month(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[AttendanceService, Depends(AttendanceService)],
    month: Annotated[str, Query(description="YYYY-MM")],
) -> Response:
    try:
        year_str, month_str = month.split("-")
        year, month_int = int(year_str), int(month_str)
        if not 1 <= month_int <= 12:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month 형식은 YYYY-MM 입니다.") from exc
    records, current_streak = await service.list_month(user.id, year, month_int)
    payload = AttendanceMonthResponse(
        month=month,
        checked_dates=[r.check_date for r in records],
        current_streak=current_streak,
        next_bonus_at=_next_bonus_at(current_streak),
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@attendance_router.post("", response_model=AttendanceCheckResponse, status_code=status.HTTP_201_CREATED)
async def check_attendance(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[AttendanceService, Depends(AttendanceService)],
) -> Response:
    payload = await service.check_in(user)
    return Response(payload, status_code=status.HTTP_201_CREATED)



def _next_bonus_at(current_streak: int) -> int | None:
    from app.services.rewards import RewardService

    for threshold in RewardService.ATTENDANCE_BONUS_THRESHOLDS:
        if threshold > current_streak:
            return threshold
    return None
