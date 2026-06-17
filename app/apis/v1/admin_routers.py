"""관리자 전용 API — 모든 엔드포인트는 get_admin_user 의존성으로 보호됩니다."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies.security import get_admin_user
from app.dtos.support import AdminFAQResponse, FAQResponse, InquiryAnswerCreateRequest, InquiryAnswerResponse, InquiryDetailResponse, InquiryListItem
from app.models.challenge import Challenge, ChallengeParticipant, ChallengeStatus
from app.models.community import Comment, Post, PostCategory, Report, ReportTargetType
from app.models.support import FAQ, FAQCategory, Inquiry, InquiryStatus
from app.models.users import User
from app.repositories.support_repository import FAQRepository, InquiryRepository
from tortoise.transactions import in_transaction

admin_router = APIRouter(prefix="/admin", tags=["admin"])


# ── 통계 ──────────────────────────────────────────────────────────────────────


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_challenges: int
    active_challenges: int
    total_posts: int
    pending_inquiries: int
    pending_reports: int


@admin_router.get("/stats", response_model=AdminStats)
async def get_stats(_: Annotated[User, Depends(get_admin_user)]) -> AdminStats:
    total_users = await User.filter(is_deleted=False).count()
    active_users = await User.filter(is_deleted=False, is_active=True, is_banned=False).count()
    total_challenges = await Challenge.filter(is_deleted=False).count()
    active_challenges = await Challenge.filter(is_deleted=False, status=ChallengeStatus.ACTIVE).count()
    total_posts = await Post.filter(is_deleted=False).count()
    pending_inquiries = await Inquiry.filter(status=InquiryStatus.PENDING).count()
    pending_reports = await Report.all().count()
    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_challenges=total_challenges,
        active_challenges=active_challenges,
        total_posts=total_posts,
        pending_inquiries=pending_inquiries,
        pending_reports=pending_reports,
    )


# ── 회원 관리 ─────────────────────────────────────────────────────────────────


class AdminUserItem(BaseModel):
    id: str
    email: str
    name: str
    nickname: str | None
    created_at: str
    last_login: str | None
    is_active: bool
    is_banned: bool
    ban_reason: str | None
    report_count: int


class AdminUserDetail(AdminUserItem):
    phone_number: str
    post_count: int
    comment_count: int


class BanRequest(BaseModel):
    reason: str


@admin_router.get("/users", response_model=list[AdminUserItem])
async def list_users(
    admin: Annotated[User, Depends(get_admin_user)],
    offset: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
    search: str | None = Query(None),  # noqa: B008
) -> list[AdminUserItem]:
    qs = User.filter(is_deleted=False)
    if search:
        from tortoise.expressions import Q  # noqa: PLC0415
        qs = qs.filter(Q(email__icontains=search) | Q(nickname__icontains=search) | Q(name__icontains=search))
    users = await qs.order_by("-created_at").offset(offset).limit(limit)
    result = []
    for u in users:
        report_count = await Report.filter(reporter_id=u.id).count()
        result.append(AdminUserItem(
            id=str(u.id),
            email=u.email,
            name=u.name,
            nickname=u.nickname,
            created_at=u.created_at.isoformat(),
            last_login=u.last_login.isoformat() if u.last_login else None,
            is_active=u.is_active,
            is_banned=u.is_banned,
            ban_reason=u.ban_reason,
            report_count=report_count,
        ))
    return result


@admin_router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: UUID,
    _: Annotated[User, Depends(get_admin_user)],
) -> AdminUserDetail:
    u = await User.get_or_none(id=user_id, is_deleted=False)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    report_count = await Report.filter(reporter_id=u.id).count()
    post_count = await Post.filter(author_id=u.id, is_deleted=False).count()
    comment_count = await Comment.filter(author_id=u.id).count()
    return AdminUserDetail(
        id=str(u.id),
        email=u.email,
        name=u.name,
        nickname=u.nickname,
        phone_number=u.phone_number,
        created_at=u.created_at.isoformat(),
        last_login=u.last_login.isoformat() if u.last_login else None,
        is_active=u.is_active,
        is_banned=u.is_banned,
        ban_reason=u.ban_reason,
        report_count=report_count,
        post_count=post_count,
        comment_count=comment_count,
    )


@admin_router.post("/users/{user_id}/ban", status_code=status.HTTP_204_NO_CONTENT)
async def ban_user(
    user_id: UUID,
    body: BanRequest,
    admin: Annotated[User, Depends(get_admin_user)],
) -> None:
    u = await User.get_or_none(id=user_id, is_deleted=False)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    if u.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자는 강퇴할 수 없습니다.")
    from datetime import datetime, timezone  # noqa: PLC0415
    await u.update_from_dict({
        "is_banned": True,
        "ban_reason": body.reason,
        "banned_at": datetime.now(timezone.utc),
        "banned_by": admin.id,
    })
    await u.save()


@admin_router.delete("/users/{user_id}/ban", status_code=status.HTTP_204_NO_CONTENT)
async def unban_user(
    user_id: UUID,
    _: Annotated[User, Depends(get_admin_user)],
) -> None:
    u = await User.get_or_none(id=user_id, is_deleted=False)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    await u.update_from_dict({"is_banned": False, "ban_reason": None, "banned_at": None, "banned_by": None})
    await u.save()


# ── 챌린지 관리 ───────────────────────────────────────────────────────────────


class AdminChallengeItem(BaseModel):
    id: int
    title: str
    scope: str
    status: str
    category: str
    participant_count: int
    start_date: str
    end_date: str
    created_at: str


@admin_router.get("/challenges", response_model=list[AdminChallengeItem])
async def list_challenges(
    _: Annotated[User, Depends(get_admin_user)],
    offset: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
    challenge_status: str | None = Query(None, alias="status"),  # noqa: B008
) -> list[AdminChallengeItem]:
    from datetime import date  # noqa: PLC0415

    from tortoise.expressions import Q  # noqa: PLC0415

    from app.apis.v1.challenge_routers import _effective_status  # noqa: PLC0415

    today = date.today()
    # 표시·필터 모두 _effective_status 규칙(end_date 지난 ACTIVE/RECRUITING=완료)에 맞춘다.
    # 취소(CANCELLED)는 soft_delete 가 is_deleted=True 로 만들므로, 취소 탭에서는 is_deleted 를
    # 거르지 않아야 보인다(기존엔 항상 is_deleted=False 로 시작해 취소 챌린지가 영구 누락됐다).
    if challenge_status == ChallengeStatus.COMPLETED.value:
        qs = Challenge.filter(
            Q(is_deleted=False),
            Q(status=ChallengeStatus.COMPLETED)
            | Q(status__in=[ChallengeStatus.ACTIVE, ChallengeStatus.RECRUITING], end_date__lt=today),
        )
    elif challenge_status == ChallengeStatus.ACTIVE.value:
        qs = Challenge.filter(is_deleted=False, status=ChallengeStatus.ACTIVE, end_date__gte=today)
    elif challenge_status == ChallengeStatus.RECRUITING.value:
        qs = Challenge.filter(is_deleted=False, status=ChallengeStatus.RECRUITING, end_date__gte=today)
    elif challenge_status == ChallengeStatus.CANCELLED.value:
        qs = Challenge.filter(status=ChallengeStatus.CANCELLED)
    else:
        qs = Challenge.filter(is_deleted=False)
    challenges = await qs.order_by("-created_at").offset(offset).limit(limit)
    result = []
    for c in challenges:
        count = await ChallengeParticipant.filter(challenge_id=c.id).count()
        result.append(AdminChallengeItem(
            id=c.id,
            title=c.title,
            scope=c.scope,
            status=_effective_status(c.status, c.end_date),
            category=c.category,
            participant_count=count,
            start_date=str(c.start_date),
            end_date=str(c.end_date),
            created_at=c.created_at.isoformat(),
        ))
    return result


# ── 신고 관리 ─────────────────────────────────────────────────────────────────


class AdminReportItem(BaseModel):
    id: int
    target_type: str
    target_id: int
    reason: str
    reporter_id: str
    created_at: str
    # 신고된 게시글/댓글의 작성자·내용(관리자가 누가 무엇을 썼는지 확인용).
    # POST/COMMENT 만 매핑하며, 대상이 이미 삭제됐으면 target_exists=False.
    author_nickname: str | None = None
    author_name: str | None = None
    content_preview: str | None = None
    target_exists: bool = True


_REPORT_PREVIEW_LEN = 100


async def _resolve_report_target(target_type: str, target_id: int) -> tuple[str | None, str | None, str | None, bool]:
    """신고 대상의 (작성자 닉네임, 작성자 이름, 내용 미리보기, 대상 존재여부) 를 반환."""
    if target_type == ReportTargetType.POST:
        post = await Post.get_or_none(id=target_id)
        if post is None:
            return None, None, None, False
        author = await post.author
        return author.nickname, author.name, f"{post.title} · {post.content}"[:_REPORT_PREVIEW_LEN], True
    if target_type == ReportTargetType.COMMENT:
        comment = await Comment.get_or_none(id=target_id)
        if comment is None:
            return None, None, None, False
        author = await comment.author
        return author.nickname, author.name, comment.content[:_REPORT_PREVIEW_LEN], True
    # VERIFICATION / CHALLENGE_PARTICIPANT 등은 작성자·본문 매핑이 달라 현재 미지원(null).
    return None, None, None, True


@admin_router.get("/reports", response_model=list[AdminReportItem])
async def list_reports(
    _: Annotated[User, Depends(get_admin_user)],
    offset: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
) -> list[AdminReportItem]:
    reports = await Report.all().order_by("-created_at").offset(offset).limit(limit)
    items: list[AdminReportItem] = []
    for r in reports:
        nickname, name, preview, exists = await _resolve_report_target(r.target_type, r.target_id)
        items.append(
            AdminReportItem(
                id=r.id,
                target_type=r.target_type,
                target_id=r.target_id,
                reason=r.reason,
                reporter_id=str(r.reporter_id),
                created_at=r.created_at.isoformat(),
                author_nickname=nickname,
                author_name=name,
                content_preview=preview,
                target_exists=exists,
            )
        )
    return items


@admin_router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_report(
    report_id: int,
    _: Annotated[User, Depends(get_admin_user)],
) -> None:
    report = await Report.get_or_none(id=report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="신고를 찾을 수 없습니다.")
    await report.delete()


@admin_router.delete("/community/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    _: Annotated[User, Depends(get_admin_user)],
) -> None:
    post = await Post.get_or_none(id=post_id, is_deleted=False)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    post.is_deleted = True
    await post.save()


@admin_router.delete("/community/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    _: Annotated[User, Depends(get_admin_user)],
) -> None:
    comment = await Comment.get_or_none(id=comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")
    await comment.delete()


# ── 문의 관리 (전체 목록) ─────────────────────────────────────────────────────


class AdminInquiryItem(BaseModel):
    id: int
    user_email: str
    title: str
    category: str
    status: str
    created_at: str


@admin_router.get("/inquiries", response_model=list[AdminInquiryItem])
async def list_all_inquiries(
    _: Annotated[User, Depends(get_admin_user)],
    offset: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
    inquiry_status: str | None = Query(None, alias="status"),  # noqa: B008
) -> list[AdminInquiryItem]:
    qs = Inquiry.all().prefetch_related("user")
    if inquiry_status:
        qs = qs.filter(status=inquiry_status)
    inquiries = await qs.order_by("-created_at").offset(offset).limit(limit)
    return [
        AdminInquiryItem(
            id=i.id,
            user_email=i.user.email,
            title=i.title,
            category=i.category,
            status=i.status,
            created_at=i.created_at.isoformat(),
        )
        for i in inquiries
    ]


@admin_router.get("/inquiries/{inquiry_id}", response_model=InquiryDetailResponse)
async def get_inquiry_detail(
    inquiry_id: int,
    _: Annotated[User, Depends(get_admin_user)],
) -> InquiryDetailResponse:
    repo = InquiryRepository()
    inquiry = await repo.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    answer_obj = await repo.get_answer(inquiry_id)
    answer = InquiryAnswerResponse.model_validate(answer_obj) if answer_obj else None
    return InquiryDetailResponse(
        **InquiryListItem.model_validate(inquiry).model_dump(),
        content=inquiry.content,
        attachment_url=inquiry.attachment_url,
        answer=answer,
    )


@admin_router.post(
    "/inquiries/{inquiry_id}/answer",
    response_model=InquiryAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def answer_inquiry(
    inquiry_id: int,
    body: InquiryAnswerCreateRequest,
    _: Annotated[User, Depends(get_admin_user)],
) -> InquiryAnswerResponse:
    repo = InquiryRepository()
    async with in_transaction():
        inquiry = await repo.get_inquiry_locked(inquiry_id)
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
        if await repo.get_answer(inquiry_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 답변이 완료된 문의입니다.")
        answer = await repo.create_answer(inquiry, body.content)
    return InquiryAnswerResponse.model_validate(answer)


# ── FAQ 관리 ──────────────────────────────────────────────────────────────────


class FAQCreateRequest(BaseModel):
    question: str
    answer: str
    category: FAQCategory
    order: int = 0


class FAQUpdateRequest(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: FAQCategory | None = None
    order: int | None = None


@admin_router.get("/faqs", response_model=list[AdminFAQResponse])
async def list_faqs_admin(
    _: Annotated[User, Depends(get_admin_user)],
    show_deleted: bool = Query(False),  # noqa: B008
) -> list[AdminFAQResponse]:
    qs = FAQ.all()
    qs = qs.filter(is_deleted=show_deleted)
    faqs = await qs.order_by("order", "id")
    return [AdminFAQResponse.model_validate(f) for f in faqs]


@admin_router.post("/faqs", response_model=AdminFAQResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    body: FAQCreateRequest,
    _: Annotated[User, Depends(get_admin_user)],
) -> AdminFAQResponse:
    faq = await FAQ.create(
        question=body.question,
        answer=body.answer,
        category=body.category,
        order=body.order,
    )
    return AdminFAQResponse.model_validate(faq)


@admin_router.patch("/faqs/{faq_id}", response_model=AdminFAQResponse)
async def update_faq(
    faq_id: int,
    body: FAQUpdateRequest,
    _: Annotated[User, Depends(get_admin_user)],
) -> AdminFAQResponse:
    faq = await FAQ.get_or_none(id=faq_id, is_deleted=False)
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ를 찾을 수 없습니다.")
    update_data = body.model_dump(exclude_none=True)
    if update_data:
        await faq.update_from_dict(update_data)
        await faq.save()
    return AdminFAQResponse.model_validate(faq)


@admin_router.delete("/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: int,
    _: Annotated[User, Depends(get_admin_user)],
) -> None:
    faq = await FAQ.get_or_none(id=faq_id, is_deleted=False)
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ를 찾을 수 없습니다.")
    faq.is_deleted = True
    await faq.save()


# ── 공지사항 관리 (PostCategory.NOTICE) ──────────────────────────────────────


class AdminNoticeItem(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
    author_name: str | None
    is_deleted: bool = False
    is_pinned: bool = False


class AdminNoticeCreateRequest(BaseModel):
    title: str
    content: str


class AdminNoticeUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


@admin_router.get("/notices", response_model=list[AdminNoticeItem])
async def list_notices(
    _: Annotated[User, Depends(get_admin_user)],
    offset: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(20, ge=1, le=100),  # noqa: B008
    show_deleted: bool = Query(False),  # noqa: B008
) -> list[AdminNoticeItem]:
    qs = Post.filter(category=PostCategory.NOTICE)
    if not show_deleted:
        qs = qs.filter(is_deleted=False)
    posts = await qs.prefetch_related("author").order_by("-created_at").offset(offset).limit(limit)
    return [
        AdminNoticeItem(
            id=p.id,
            title=p.title,
            content=p.content,
            created_at=p.created_at.isoformat(),
            author_name=p.author.nickname or p.author.name if p.author else None,
            is_deleted=p.is_deleted,
            is_pinned=p.is_pinned,
        )
        for p in posts
    ]


@admin_router.post("/notices", response_model=AdminNoticeItem, status_code=status.HTTP_201_CREATED)
async def create_notice(
    body: AdminNoticeCreateRequest,
    admin: Annotated[User, Depends(get_admin_user)],
) -> AdminNoticeItem:
    post = await Post.create(
        title=body.title,
        content=body.content,
        category=PostCategory.NOTICE,
        author_id=admin.id,
    )
    return AdminNoticeItem(
        id=post.id,
        title=post.title,
        content=post.content,
        created_at=post.created_at.isoformat(),
        author_name=admin.nickname or admin.name,
        is_pinned=post.is_pinned,
    )


@admin_router.patch("/notices/{notice_id}", response_model=AdminNoticeItem)
async def update_notice(
    notice_id: int,
    body: AdminNoticeUpdateRequest,
    admin: Annotated[User, Depends(get_admin_user)],
) -> AdminNoticeItem:
    post = await Post.get_or_none(id=notice_id, category=PostCategory.NOTICE, is_deleted=False)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다.")
    update_data = body.model_dump(exclude_none=True)
    if update_data:
        await post.update_from_dict(update_data)
        await post.save()
    return AdminNoticeItem(
        id=post.id,
        title=post.title,
        content=post.content,
        created_at=post.created_at.isoformat(),
        author_name=admin.nickname or admin.name,
        is_pinned=post.is_pinned,
    )


@admin_router.delete("/notices/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notice(
    notice_id: int,
    _: Annotated[User, Depends(get_admin_user)],
) -> None:
    post = await Post.get_or_none(id=notice_id, category=PostCategory.NOTICE, is_deleted=False)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다.")
    post.is_deleted = True
    await post.save()


_MAX_PINNED = 3


@admin_router.patch("/notices/{notice_id}/pin", response_model=AdminNoticeItem)
async def toggle_pin_notice(
    notice_id: int,
    admin: Annotated[User, Depends(get_admin_user)],
) -> AdminNoticeItem:
    post = await Post.get_or_none(id=notice_id, category=PostCategory.NOTICE, is_deleted=False)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다.")
    if not post.is_pinned:
        pinned_count = await Post.filter(
            category=PostCategory.NOTICE, is_pinned=True, is_deleted=False
        ).count()
        if pinned_count >= _MAX_PINNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"고정 게시글은 최대 {_MAX_PINNED}개까지 설정할 수 있습니다.",
            )
    post.is_pinned = not post.is_pinned
    await post.save(update_fields=["is_pinned"])
    author = await post.author
    return AdminNoticeItem(
        id=post.id,
        title=post.title,
        content=post.content,
        created_at=post.created_at.isoformat(),
        author_name=author.nickname or author.name if author else None,
        is_pinned=post.is_pinned,
    )
