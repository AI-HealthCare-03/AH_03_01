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
        # sign_media_url 은 str|None 반환(공개 경로는 입력 그대로, 비공개만 서명).
        # access_url 은 non-null 이므로 None 이 될 일은 없고, `or value` 는 타입 가드용.
        return sign_media_url(value) or value
