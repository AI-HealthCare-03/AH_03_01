from datetime import datetime

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
