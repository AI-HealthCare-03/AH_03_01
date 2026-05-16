from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, status

from app.core import config
from app.models.files import FileType, FileUpload
from app.models.users import User
from app.repositories.files_repository import FileUploadRepository

CHUNK_SIZE = 64 * 1024


class FileUploadService:
    def __init__(self) -> None:
        self.repo = FileUploadRepository()

    async def upload(
        self,
        user: User,
        *,
        upload_file_stream: BinaryIO,
        original_name: str,
        mime_type: str,
        file_type: FileType,
    ) -> FileUpload:
        if mime_type not in config.ALLOWED_IMAGE_MIME and file_type in {
            FileType.CHALLENGE_VERIFICATION,
            FileType.PROFILE_IMAGE,
            FileType.POST_ATTACHMENT,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 이미지 형식입니다: {mime_type}",
            )

        # 사용자별 디렉터리. 충돌 방지를 위해 random hex prefix.
        today = datetime.now(config.TIMEZONE).strftime("%Y%m%d")
        random_id = secrets.token_hex(8)
        suffix = Path(original_name).suffix.lower() or ""
        stored_filename = f"{random_id}{suffix}"
        rel_dir = Path("uploads") / file_type.value.lower() / today / str(user.id)
        abs_dir = Path(config.MEDIA_ROOT) / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        abs_path = abs_dir / stored_filename

        # 스트리밍 저장 + 사이즈 제한 검증
        total_bytes = 0
        with abs_path.open("wb") as out:
            while True:
                chunk = upload_file_stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > config.UPLOAD_MAX_BYTES:
                    out.close()
                    abs_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"파일 크기는 최대 {config.UPLOAD_MAX_BYTES // (1024 * 1024)}MB 입니다.",
                    )
                out.write(chunk)

        access_url = f"{config.MEDIA_URL_PREFIX}/{rel_dir.as_posix()}/{stored_filename}"

        return await self.repo.create(
            {
                "uploader_id": user.id,
                "file_type": file_type,
                "original_name": original_name[:255],
                "stored_path": str(abs_path),
                "access_url": access_url,
                "mime_type": mime_type,
                "file_size_bytes": total_bytes,
                "is_resized": False,
            }
        )

    async def get_for_user(self, file_id: int) -> FileUpload | None:
        return await self.repo.get(file_id)
