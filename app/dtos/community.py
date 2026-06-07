from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel
from app.models.community import PostCategory


class PostListItem(BaseSerializerModel):
    id: int
    title: str
    category: PostCategory
    is_pinned: bool
    view_count: int
    author_id: UUID
    author_nickname: str | None
    created_at: datetime


class PostDetailResponse(PostListItem):
    content: str
    updated_at: datetime


class PostListResponse(BaseModel):
    items: list[PostListItem]
    total: int
    page: int
    size: int
