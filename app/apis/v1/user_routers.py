from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.users import PasswordChangeRequest, UserInfoResponse, UserUpdateRequest
from app.models.files import FileUpload
from app.models.users import User
from app.services.users import UserManageService


async def _build_user_info_response(user: User) -> UserInfoResponse:
    """avatar_url 을 file 메타에서 채워 응답으로 변환."""
    payload = UserInfoResponse.model_validate(user)
    if user.avatar_file_id:
        file_record = await FileUpload.get_or_none(id=user.avatar_file_id)
        if file_record is not None:
            payload.avatar_url = file_record.access_url
    return payload


user_router = APIRouter(prefix="/users", tags=["users"])


class UserSearchItem(BaseModel):
    id: UUID
    name: str


class UserSearchResponse(BaseModel):
    items: list[UserSearchItem]


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    payload = await _build_user_info_response(user)
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@user_router.get("/search", response_model=UserSearchResponse, status_code=status.HTTP_200_OK)
async def search_users(
    user: Annotated[User, Depends(get_request_user)],
    nickname: Annotated[str, Query(min_length=1, max_length=10)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> Response:
    """닉네임(부분 일치)으로 활성 사용자 검색. 자기 자신은 제외.

    nickname 이 비어 있는 레거시 사용자도 검색할 수 있도록 name 으로 fallback.
    """
    keyword = nickname.strip()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="nickname 이 필요합니다.")
    from tortoise.expressions import Q  # noqa: PLC0415

    rows = (
        await User.filter(
            Q(nickname__icontains=keyword) | Q(nickname__isnull=True, name__icontains=keyword),
            is_active=True,
        )
        .exclude(id=user.id)
        .order_by("nickname", "name")
        .limit(limit)
        .values("id", "nickname", "name")
    )
    payload = UserSearchResponse(
        items=[UserSearchItem(id=r["id"], name=str(r["nickname"] or r["name"])) for r in rows],
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@user_router.patch("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    payload = await _build_user_info_response(updated_user)
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@user_router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    body: PasswordChangeRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    await user_manage_service.change_password(user=user, data=body)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)
