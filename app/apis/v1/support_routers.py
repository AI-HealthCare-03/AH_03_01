from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.security import get_request_user
from app.dtos.support import (
    FAQResponse,
    InquiryAnswerResponse,
    InquiryCreateRequest,
    InquiryDetailResponse,
    InquiryListItem,
    InquiryUpdateRequest,
)
from app.models.support import FAQCategory, InquiryStatus
from app.models.users import User
from app.repositories.support_repository import FAQRepository, InquiryRepository

support_router = APIRouter(prefix="/support", tags=["support"])


# ── FAQ ───────────────────────────────────────────────────────────────────────


@support_router.get("/faqs", response_model=list[FAQResponse])
async def list_faqs(
    category: FAQCategory | None = Query(None),  # noqa: B008
    _: User = Depends(get_request_user),  # noqa: B008
) -> list[FAQResponse]:
    faqs = await FAQRepository().list_faqs(category)
    return [FAQResponse.model_validate(f) for f in faqs]


# ── 1:1 문의 ──────────────────────────────────────────────────────────────────


@support_router.get("/inquiries", response_model=list[InquiryListItem])
async def list_inquiries(current_user: User = Depends(get_request_user)) -> list[InquiryListItem]:  # noqa: B008
    inquiries = await InquiryRepository().list_inquiries(current_user.id)
    return [InquiryListItem.model_validate(i) for i in inquiries]


@support_router.post("/inquiries", response_model=InquiryDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    body: InquiryCreateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> InquiryDetailResponse:
    inquiry = await InquiryRepository().create_inquiry(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        category=body.category,
        attachment_url=body.attachment_url,
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
    inquiry = await repo.get_inquiry(inquiry_id)
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
    inquiry = await repo.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    if inquiry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="삭제 권한이 없습니다.")
    if inquiry.status != InquiryStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="답변 완료된 문의는 삭제할 수 없습니다.")
    await repo.delete_inquiry(inquiry)
