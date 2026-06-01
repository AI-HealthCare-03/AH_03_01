from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel
from app.models.chatbot import ChatMessageRole, ChatMessageType, FaqCategory


class FaqResponse(BaseSerializerModel):
    id: int
    category: FaqCategory
    question: str
    answer: str
    sort_order: int


class FaqListResponse(BaseModel):
    faqs: list[FaqResponse]


class ChatMessageRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    conversation_id: int | None = None
    faq_id: int | None = None


class ChatSourceItem(BaseModel):
    title: str | None = None
    url: str | None = None
    document_id: int | None = None
    snippet: str | None = None
    source: str | None = None  # 문서 코드 (예: "KSH2022") — 프론트 문서명 라벨링용


class ChatMessageResponse(BaseModel):
    # ── 기존 필드 (변경 없음) ────────────────────────────────
    conversation_id: int
    message_id: int
    role: ChatMessageRole
    message_type: ChatMessageType
    answer: str
    sources: list[ChatSourceItem] = []
    confidence: float | None = None
    model_version: str | None = None
    disclaimer: str = "본 답변은 의학적 진단을 대체하지 않습니다."
    # ── 신규 필드 (ChatRAGGraph 결과 표현, API 계약 v1) ───────
    intent: str | None = None
    # needs_health_data: 질문이 본인 데이터를 요구하는지 (classify 결과).
    # has_health_data: 사용자가 DB 에 의미 있는 데이터를 갖고 있는지 (fetch 결과).
    # 프론트 분기: needs_health_data=true && has_health_data=false 일 때만 CTA 표시.
    needs_health_data: bool = False
    has_health_data: bool = False
    missing_fields: list[str] = []
    action_hint: str | None = None
    is_fallback: bool = False
    eval_revision_count: int | None = None


class ChatSessionListItem(BaseModel):
    id: int
    title: str | None
    started_at: datetime
    ended_at: datetime | None
    last_message_at: datetime | None
    message_count: int


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionListItem]


class ChatMessageItem(BaseModel):
    id: int
    role: ChatMessageRole
    message_type: ChatMessageType
    content: str
    faq_id: int | None
    sources: list[dict[str, Any]] = []
    confidence: float | None
    created_at: datetime


class ChatSessionDetailResponse(BaseModel):
    id: int
    title: str | None
    started_at: datetime
    ended_at: datetime | None
    messages: list[ChatMessageItem]
