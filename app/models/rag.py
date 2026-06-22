from enum import StrEnum
from typing import Any

from tortoise import fields, models

from app.core.db.fields import VectorField

DEFAULT_EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small


class DocumentType(StrEnum):
    GUIDELINE = "GUIDELINE"
    FAQ = "FAQ"
    EDUCATION = "EDUCATION"
    NOTICE = "NOTICE"
    OTHER = "OTHER"


class RAGDocument(models.Model):
    """RAG / 챗봇 검색용 문서 청크.

    embedding 컬럼은 PGVector `vector(1536)` 로 저장된다. 유사도 검색은
    raw SQL(`embedding <=> $1`) 로 수행한다.
    """

    id = fields.BigIntField(primary_key=True)
    document_type = fields.CharEnumField(enum_type=DocumentType, default=DocumentType.OTHER)
    source = fields.CharField(max_length=200)
    title = fields.CharField(max_length=200, null=True)
    chunk_index = fields.IntField(default=0)
    chunk_text = fields.TextField()
    embedding: list[float] | None = VectorField(dimensions=DEFAULT_EMBEDDING_DIM, null=True)  # type: ignore[assignment]
    metadata: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "rag_documents"
        indexes = [("document_type", "source"), ("is_active",)]
