from enum import StrEnum
from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class FaqCategory(StrEnum):
    SERVICE = "SERVICE"
    DISEASE = "DISEASE"
    CHALLENGE = "CHALLENGE"
    ACCOUNT = "ACCOUNT"


class ChatMessageRole(StrEnum):
    USER = "USER"
    BOT = "BOT"


class ChatMessageType(StrEnum):
    TEXT = "TEXT"
    FAQ = "FAQ"
    RAG = "RAG"
    SYSTEM = "SYSTEM"


class ChatbotFaq(models.Model):
    id = fields.BigIntField(primary_key=True)
    admin_id = fields.BigIntField(null=True)  # FK to ADMIN; 별도 admin 도메인 추가 시 연결
    category = fields.CharEnumField(enum_type=FaqCategory)
    question = fields.CharField(max_length=200)
    answer = fields.TextField()
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chatbot_faqs"
        indexes = [("category", "is_active", "sort_order")]


class ChatbotSession(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="chatbot_sessions", on_delete=fields.CASCADE
    )
    user_id: int
    title = fields.CharField(max_length=120, null=True)
    started_at = fields.DatetimeField(auto_now_add=True)
    ended_at = fields.DatetimeField(null=True)
    last_message_at = fields.DatetimeField(null=True)
    message_count = fields.IntField(default=0)

    class Meta:
        table = "chatbot_sessions"
        indexes = [("user_id", "started_at")]


class ChatbotMessage(models.Model):
    id = fields.BigIntField(primary_key=True)
    session: fields.ForeignKeyRelation["ChatbotSession"] = fields.ForeignKeyField(
        "models.ChatbotSession", related_name="messages", on_delete=fields.CASCADE
    )
    session_id: int
    role = fields.CharEnumField(enum_type=ChatMessageRole)
    message_type = fields.CharEnumField(enum_type=ChatMessageType, default=ChatMessageType.TEXT)
    content = fields.TextField()
    faq: fields.ForeignKeyNullableRelation["ChatbotFaq"] = fields.ForeignKeyField(
        "models.ChatbotFaq", related_name="messages", null=True, on_delete=fields.SET_NULL
    )
    faq_id: int | None
    sources = fields.JSONField(default=list)  # type: ignore[var-annotated]
    confidence = fields.FloatField(null=True)
    model_version = fields.CharField(max_length=40, null=True)
    # ChatRAGGraph 결과의 부가 메타 (intent/needs_health_data/missing_fields/action_hint/
    # is_fallback/eval_revision_count/disclaimer). 이력 조회·디버깅·평가용. null 허용.
    extra_data: dict[str, Any] | None = fields.JSONField(null=True)  # type: ignore[assignment]
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chatbot_messages"
        indexes = [("session_id", "created_at")]
