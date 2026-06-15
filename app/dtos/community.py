from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel
from app.models.community import InfoCategory, PostCategory, QuizCategory, QuizOption, ReportReason, ReportTargetType


class PostListItem(BaseSerializerModel):
    id: int
    title: str
    category: PostCategory
    info_category: InfoCategory | None = None
    is_pinned: bool
    view_count: int
    comment_count: int
    like_count: int = 0
    author_id: UUID
    author_nickname: str | None
    created_at: datetime


class PostDetailResponse(PostListItem):
    content: str
    updated_at: datetime
    is_liked: bool = False


class PostListResponse(BaseModel):
    items: list[PostListItem]
    total: int
    page: int
    size: int


class PostCreateRequest(BaseModel):
    title: str
    content: str
    category: PostCategory
    info_category: InfoCategory | None = None


class PostUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    category: PostCategory | None = None
    info_category: InfoCategory | None = None


class CommentResponse(BaseSerializerModel):
    id: int
    content: str
    author_id: UUID
    author_nickname: str | None
    parent_id: int | None
    created_at: datetime
    updated_at: datetime
    like_count: int = 0
    is_liked: bool = False
    replies: list["CommentResponse"] = []


CommentResponse.model_rebuild()


class CommentCreateRequest(BaseModel):
    content: str
    parent_id: int | None = None


class CommentUpdateRequest(BaseModel):
    content: str


class LikeResponse(BaseModel):
    like_count: int
    is_liked: bool


class ReportCreateRequest(BaseModel):
    target_type: ReportTargetType
    target_id: int
    reason: ReportReason


# ── Quiz DTOs ──────────────────────────────────────────────────────────────────


class QuizResponse(BaseSerializerModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    category: QuizCategory
    quiz_date: date | None


class QuizAnswerRequest(BaseModel):
    selected_option: QuizOption


class QuizAnswerResponse(BaseSerializerModel):
    is_correct: bool
    correct_option: QuizOption
    explanation: str
    points_earned: int


class QuizAttemptHistoryItem(BaseSerializerModel):
    quiz_id: int
    quiz_date: date | None
    question: str
    category: QuizCategory
    selected_option: QuizOption
    is_correct: bool
    points_earned: int
    attempted_at: datetime
