from fastapi import APIRouter, Depends, HTTPException, Query, status
from tortoise.transactions import in_transaction

from app.dependencies.security import get_admin_user, get_request_user
from app.dtos.support import (
    FAQResponse,
    InquiryAnswerCreateRequest,
    InquiryAnswerResponse,
    InquiryCreateRequest,
    InquiryDetailResponse,
    InquiryListItem,
    InquiryUpdateRequest,
)
from app.models.support import FAQCategory, InquiryStatus
from app.models.users import User
from app.repositories.files_repository import FileUploadRepository
from app.repositories.support_repository import FAQRepository, InquiryRepository

support_router = APIRouter(prefix="/support", tags=["support"])


# ── FAQ ───────────────────────────────────────────────────────────────────────


@support_router.get("/faqs", response_model=list[FAQResponse])
async def list_faqs(
    category: FAQCategory | None = Query(None),  # noqa: B008
) -> list[FAQResponse]:
    faqs = await FAQRepository().list_faqs(category)
    return [FAQResponse.model_validate(f) for f in faqs]


# ── 1:1 문의 ──────────────────────────────────────────────────────────────────


@support_router.get("/inquiries", response_model=list[InquiryListItem])
async def list_inquiries(
    offset: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> list[InquiryListItem]:
    inquiries = await InquiryRepository().list_inquiries(current_user.id, offset=offset, limit=limit)
    return [InquiryListItem.model_validate(i) for i in inquiries]


@support_router.post("/inquiries", response_model=InquiryDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    body: InquiryCreateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> InquiryDetailResponse:
    attachment_url: str | None = None
    if body.attachment_file_id is not None:
        file = await FileUploadRepository().get_owned(body.attachment_file_id, current_user.id)
        if file is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="첨부 파일 접근 권한이 없습니다.")
        attachment_url = file.access_url
    inquiry = await InquiryRepository().create_inquiry(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        category=body.category,
        attachment_url=attachment_url,
    )
    return InquiryDetailResponse(
        **InquiryListItem.model_validate(inquiry).model_dump(),
        content=inquiry.content,
        attachment_url=inquiry.attachment_url,
        answer=None,
    )


@support_router.get("/inquiries/{inquiry_id}", response_model=InquiryDetailResponse)
async def get_inquiry(
    inquiry_id: int,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> InquiryDetailResponse:
    repo = InquiryRepository()
    inquiry = await repo.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    if inquiry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="조회 권한이 없습니다.")
    answer_obj = await repo.get_answer(inquiry_id)
    answer = InquiryAnswerResponse.model_validate(answer_obj) if answer_obj else None
    return InquiryDetailResponse(
        **InquiryListItem.model_validate(inquiry).model_dump(),
        content=inquiry.content,
        attachment_url=inquiry.attachment_url,
        answer=answer,
    )


@support_router.patch("/inquiries/{inquiry_id}", response_model=InquiryDetailResponse)
async def update_inquiry(
    inquiry_id: int,
    body: InquiryUpdateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> InquiryDetailResponse:
    repo = InquiryRepository()
    async with in_transaction():
        inquiry = await repo.get_inquiry_locked(inquiry_id)
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
        if inquiry.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다.")
        if inquiry.status != InquiryStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="답변 완료된 문의는 수정할 수 없습니다.")
        inquiry = await repo.update_inquiry(inquiry, title=body.title, content=body.content)
    return InquiryDetailResponse(
        **InquiryListItem.model_validate(inquiry).model_dump(),
        content=inquiry.content,
        attachment_url=inquiry.attachment_url,
        answer=None,
    )


@support_router.delete("/inquiries/{inquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inquiry(
    inquiry_id: int,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> None:
    repo = InquiryRepository()
    async with in_transaction():
        inquiry = await repo.get_inquiry_locked(inquiry_id)
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
        if inquiry.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="삭제 권한이 없습니다.")
        if inquiry.status != InquiryStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="답변 완료된 문의는 삭제할 수 없습니다.")
        await repo.delete_inquiry(inquiry)


@support_router.post(
    "/inquiries/{inquiry_id}/answer",
    response_model=InquiryAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inquiry_answer(
    inquiry_id: int,
    body: InquiryAnswerCreateRequest,
    _: User = Depends(get_admin_user),  # noqa: B008
) -> InquiryAnswerResponse:
    repo = InquiryRepository()
    async with in_transaction():
        inquiry = await repo.get_inquiry_locked(inquiry_id)
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
        existing_answer = await repo.get_answer(inquiry_id)
        if existing_answer:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 답변이 완료된 문의입니다.")
        answer = await repo.create_answer(inquiry, body.content)
    return InquiryAnswerResponse.model_validate(answer)
