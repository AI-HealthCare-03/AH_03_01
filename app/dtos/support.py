from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.core.media import sign_media_url
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

    @field_serializer("attachment_url")
    def _sign_attachment_url(self, value: str | None) -> str | None:
        return sign_media_url(value)


class InquiryCreateRequest(BaseModel):
    title: str = Field(max_length=200)
    content: str = Field(max_length=5000)
    category: InquiryCategory
    attachment_file_id: int | None = None


class InquiryUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=5000)


class InquiryAnswerCreateRequest(BaseModel):
    content: str = Field(max_length=5000)
