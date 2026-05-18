from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class FileType(StrEnum):
    PROFILE_IMAGE = "PROFILE_IMAGE"
    CHALLENGE_VERIFICATION = "CHALLENGE_VERIFICATION"
    POST_ATTACHMENT = "POST_ATTACHMENT"
    INQUIRY_ATTACHMENT = "INQUIRY_ATTACHMENT"
    REPORT_PDF = "REPORT_PDF"
    OTHER = "OTHER"


class FileUpload(models.Model):
    """파일 업로드 메타데이터. 실제 바이트는 stored_path 의 디스크에 저장.
    access_url 은 /media/... 정적 서빙 경로."""

    id = fields.BigIntField(primary_key=True)
    uploader: fields.ForeignKeyNullableRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="uploaded_files", null=True, on_delete=fields.SET_NULL
    )
    uploader_id: int | None
    file_type = fields.CharEnumField(enum_type=FileType, default=FileType.OTHER)
    original_name = fields.CharField(max_length=255)
    stored_path = fields.CharField(max_length=512)
    access_url = fields.CharField(max_length=512)
    mime_type = fields.CharField(max_length=80)
    file_size_bytes = fields.BigIntField(default=0)
    is_resized = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "file_uploads"
        indexes = [("uploader_id", "file_type"), ("created_at",)]
