from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class FAQCategory(StrEnum):
    ACCOUNT = "ACCOUNT"
    CHALLENGE = "CHALLENGE"
    HEALTH_DATA = "HEALTH_DATA"
    PAYMENT = "PAYMENT"


class InquiryCategory(StrEnum):
    SERVICE_INQUIRY = "SERVICE_INQUIRY"
    ACCOUNT_INQUIRY = "ACCOUNT_INQUIRY"
    ERROR_REPORT = "ERROR_REPORT"
    SANCTIONS_INQUIRY = "SANCTIONS_INQUIRY"
    ETC = "ETC"


class InquiryStatus(StrEnum):
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"


class FAQ(models.Model):
    id = fields.BigIntField(primary_key=True)
    question = fields.TextField()
    answer = fields.TextField()
    category = fields.CharEnumField(FAQCategory, max_length=20)
    order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "support_faqs"
        ordering = ["order", "id"]


class Inquiry(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="inquiries", on_delete=fields.CASCADE
    )
    title = fields.CharField(max_length=200)
    content = fields.TextField()
    category = fields.CharEnumField(InquiryCategory, max_length=30)
    attachment_url = fields.CharField(max_length=512, null=True)
    status = fields.CharEnumField(InquiryStatus, max_length=20, default=InquiryStatus.PENDING)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "support_inquiries"
        ordering = ["-created_at"]


class InquiryAnswer(models.Model):
    id = fields.BigIntField(primary_key=True)
    inquiry: fields.OneToOneRelation["Inquiry"] = fields.OneToOneField(
        "models.Inquiry", related_name="answer", on_delete=fields.CASCADE
    )
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "support_inquiry_answers"
