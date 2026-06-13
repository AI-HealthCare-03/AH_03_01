from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.dtos.base import BaseSerializerModel
from app.models.support import FAQCategory, InquiryCategory, InquiryStatus


class FAQResponse(BaseSerializerModel):
    id: int
    question: str
    answer: str
    category: FAQCategory
    order: int


class InquiryAnswerResponse(BaseSerializerModel):
    id: int
    content: str
    created_at: datetime


class InquiryListItem(BaseSerializerModel):
    id: int
    title: str
    category: InquiryCategory
    status: InquiryStatus
    created_at: datetime
    updated_at: datetime


class InquiryDetailResponse(InquiryListItem):
    content: str
    attachment_url: str | None
    answer: InquiryAnswerResponse | None


class InquiryCreateRequest(BaseModel):
    title: str = Field(max_length=200)
    content: str = Field(max_length=5000)
    category: InquiryCategory
    attachment_url: str | None = None

    @field_validator("attachment_url")
    @classmethod
    def validate_attachment_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("/media/") or ".." in v:
            raise ValueError("attachment_url은 /media/ 하위 경로만 허용됩니다.")
        return v


class InquiryUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=5000)
