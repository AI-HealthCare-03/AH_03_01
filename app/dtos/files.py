from datetime import datetime

from pydantic import field_serializer

from app.core.media import sign_media_url
from app.dtos.base import BaseSerializerModel
from app.models.files import FileType


class FileUploadResponse(BaseSerializerModel):
    id: int
    file_type: FileType
    original_name: str
    access_url: str
    mime_type: str
    file_size_bytes: int
    created_at: datetime

    @field_serializer("access_url")
    def _sign_access_url(self, value: str) -> str:
        return sign_media_url(value) or value
