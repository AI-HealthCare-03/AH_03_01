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


class PostCreateRequest(BaseModel):
    title: str
    content: str
    category: PostCategory


class PostUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    category: PostCategory | None = None


class CommentResponse(BaseSerializerModel):
    id: int
    content: str
    author_id: UUID
    author_nickname: str | None
    parent_id: int | None
    created_at: datetime
    updated_at: datetime
    replies: list["CommentResponse"] = []


CommentResponse.model_rebuild()


class CommentCreateRequest(BaseModel):
    content: str
    parent_id: int | None = None


class CommentUpdateRequest(BaseModel):
    content: str
