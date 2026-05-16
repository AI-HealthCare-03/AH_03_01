from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.files import FileUploadResponse
from app.models.files import FileType
from app.models.users import User
from app.services.files import FileUploadService

files_router = APIRouter(prefix="/files", tags=["files"])


@files_router.post(
    "",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[FileUploadService, Depends(FileUploadService)],
    file: Annotated[UploadFile, File(description="업로드할 파일")],
    purpose: Annotated[str, Form(description="profile|verification|post|inquiry|other")] = "other",
) -> Response:
    purpose_map = {
        "profile": FileType.PROFILE_IMAGE,
        "verification": FileType.CHALLENGE_VERIFICATION,
        "post": FileType.POST_ATTACHMENT,
        "inquiry": FileType.INQUIRY_ATTACHMENT,
        "other": FileType.OTHER,
    }
    file_type = purpose_map.get(purpose, FileType.OTHER)
    mime_type = file.content_type or "application/octet-stream"
    original_name = file.filename or "unnamed"

    record = await service.upload(
        user,
        upload_file_stream=file.file,
        original_name=original_name,
        mime_type=mime_type,
        file_type=file_type,
    )
    return Response(
        FileUploadResponse.model_validate(record).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@files_router.get("/{file_id}", response_model=FileUploadResponse, status_code=status.HTTP_200_OK)
async def get_file_meta(
    file_id: int,
    _: Annotated[User, Depends(get_request_user)],
    service: Annotated[FileUploadService, Depends(FileUploadService)],
) -> Response:
    record = await service.get_for_user(file_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일을 찾을 수 없습니다.")
    return Response(
        FileUploadResponse.model_validate(record).model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )
