from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse, UserUpdateRequest
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])


class UserSearchItem(BaseModel):
    id: int
    name: str


class UserSearchResponse(BaseModel):
    items: list[UserSearchItem]


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    return Response(UserInfoResponse.model_validate(user).model_dump(), status_code=status.HTTP_200_OK)


@user_router.get("/search", response_model=UserSearchResponse, status_code=status.HTTP_200_OK)
async def search_users(
    user: Annotated[User, Depends(get_request_user)],
    nickname: Annotated[str, Query(min_length=1, max_length=20)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> Response:
    """닉네임(부분 일치)으로 활성 사용자 검색. 자기 자신은 제외."""
    keyword = nickname.strip()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="nickname 이 필요합니다.")
    rows = (
        await User.filter(name__icontains=keyword, is_active=True)
        .exclude(id=user.id)
        .order_by("name")
        .limit(limit)
        .values("id", "name")
    )
    payload = UserSearchResponse(
        items=[UserSearchItem(id=int(r["id"]), name=str(r["name"])) for r in rows],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@user_router.patch("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    return Response(UserInfoResponse.model_validate(updated_user).model_dump(), status_code=status.HTTP_200_OK)
