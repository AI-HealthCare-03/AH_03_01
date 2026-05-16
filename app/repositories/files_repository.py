from typing import Any

from app.models.files import FileUpload


class FileUploadRepository:
    def __init__(self) -> None:
        self._model = FileUpload

    async def create(self, data: dict[str, Any]) -> FileUpload:
        return await self._model.create(**data)

    async def get(self, file_id: int) -> FileUpload | None:
        return await self._model.get_or_none(id=file_id)

    async def get_owned(self, file_id: int, user_id: int) -> FileUpload | None:
        return await self._model.get_or_none(id=file_id, uploader_id=user_id)
