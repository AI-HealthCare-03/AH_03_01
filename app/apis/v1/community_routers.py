from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.core import config
from app.dependencies.security import get_request_user
from app.dtos.community import (
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    PostCreateRequest,
    PostDetailResponse,
    PostListItem,
    PostListResponse,
    PostUpdateRequest,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizAttemptHistoryItem,
    QuizResponse,
    ReportCreateRequest,
)
from app.models.community import Comment, Post, PostCategory
from app.models.notifications import NotificationType
from app.models.users import User
from app.repositories.community_repository import CommentRepository, PostRepository, ReportRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.quiz import HealthQuizService

posts_router = APIRouter(prefix="/posts", tags=["community"])


def _to_item(p: Post) -> PostListItem:
    return PostListItem(
        id=p.id,
        title=p.title,
        category=p.category,
        is_pinned=p.is_pinned,
        view_count=p.view_count,
        comment_count=getattr(p, "comment_count", 0),
        author_id=p.author_id,
        author_nickname=p.author.nickname,
        created_at=p.created_at,
    )


@posts_router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_post_image(
    file: UploadFile = File(...),  # noqa: B008
    _: User = Depends(get_request_user),  # noqa: B008
) -> dict[str, str]:
    if file.content_type not in config.ALLOWED_IMAGE_MIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="허용되지 않는 파일 형식입니다.")
    contents = await file.read()
    if len(contents) > config.UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="파일 크기가 너무 큽니다.")
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid4().hex}.{ext}"
    upload_dir = Path(config.MEDIA_ROOT) / "community"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(contents)
    return {"url": f"{config.MEDIA_URL_PREFIX}/community/{filename}"}


@posts_router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),  # noqa: B008
    size: int = Query(20, ge=1, le=100),  # noqa: B008
    category: PostCategory | None = Query(None),  # noqa: B008
    _: User = Depends(get_request_user),  # noqa: B008
) -> PostListResponse:
    posts, total = await PostRepository().list_posts(page, size, category)
    return PostListResponse(items=[_to_item(p) for p in posts], total=total, page=page, size=size)


@posts_router.get("/{post_id}", response_model=PostDetailResponse)
async def get_post(post_id: int, _: User = Depends(get_request_user)) -> PostDetailResponse:  # noqa: B008
    repo = PostRepository()
    post = await repo.get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    await repo.increment_view(post.id, post.view_count)
    return PostDetailResponse(**_to_item(post).model_dump(), content=post.content, updated_at=post.updated_at)


@posts_router.post("", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_post(body: PostCreateRequest, current_user: User = Depends(get_request_user)) -> PostDetailResponse:  # noqa: B008
    repo = PostRepository()
    post = await repo.create_post(
        author_id=current_user.id, title=body.title, content=body.content, category=body.category
    )
    post = await repo.get_post(post.id)
    return PostDetailResponse(**_to_item(post).model_dump(), content=post.content, updated_at=post.updated_at)


@posts_router.patch("/{post_id}", response_model=PostDetailResponse)
async def update_post(
    post_id: int,
    body: PostUpdateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> PostDetailResponse:
    repo = PostRepository()
    post = await repo.get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다.")
    post = await repo.update_post(post, title=body.title, content=body.content, category=body.category)
    return PostDetailResponse(**_to_item(post).model_dump(), content=post.content, updated_at=post.updated_at)


@posts_router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: User = Depends(get_request_user)) -> None:  # noqa: B008
    repo = PostRepository()
    post = await repo.get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="삭제 권한이 없습니다.")
    await repo.delete_post(post)


# ── 댓글 ─────────────────────────────────────────────────────────────────────

comments_router = APIRouter(prefix="/posts/{post_id}/comments", tags=["comments"])


def _build_comment(c: Comment, replies: list[Comment] | None = None) -> CommentResponse:
    return CommentResponse(
        id=c.id,
        content=c.content,
        author_id=c.author_id,
        author_nickname=c.author.nickname,
        parent_id=c.parent_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
        replies=[_build_comment(r) for r in (replies or [])],
    )


@comments_router.get("", response_model=list[CommentResponse])
async def list_comments(post_id: int, _: User = Depends(get_request_user)) -> list[CommentResponse]:  # noqa: B008
    repo = CommentRepository()
    comments = await repo.list_comments(post_id)
    result = []
    for c in comments:
        replies = await repo.list_replies(c.id)
        result.append(_build_comment(c, replies))
    return result


@comments_router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    body: CommentCreateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> CommentResponse:
    comment = await CommentRepository().create_comment(post_id, current_user.id, body.content, body.parent_id)

    actor_name = current_user.nickname or "누군가"
    notif_repo = NotificationRepository()
    if body.parent_id is None:
        # 게시글에 새 댓글 → 게시글 작성자에게 알림
        post = await Post.get_or_none(id=post_id)
        if post and post.author_id != current_user.id:
            await notif_repo.create(
                recipient_id=post.author_id,
                actor_id=current_user.id,
                notification_type=NotificationType.COMMENT,
                target_type="POST",
                target_id=post_id,
                message=f"{actor_name}님이 내 게시글에 댓글을 남겼어요.",
            )
    else:
        # 댓글에 답글 → 원댓글 작성자에게 알림
        parent = await Comment.get_or_none(id=body.parent_id)
        if parent and parent.author_id != current_user.id:
            await notif_repo.create(
                recipient_id=parent.author_id,
                actor_id=current_user.id,
                notification_type=NotificationType.REPLY,
                target_type="COMMENT",
                target_id=body.parent_id,
                message=f"{actor_name}님이 내 댓글에 답글을 남겼어요.",
            )

    return _build_comment(comment)


@comments_router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    post_id: int,
    comment_id: int,
    body: CommentUpdateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> CommentResponse:
    repo = CommentRepository()
    comment = await repo.get_comment(comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다.")
    comment = await repo.update_comment(comment, body.content)
    return _build_comment(comment)


@comments_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> None:
    repo = CommentRepository()
    comment = await repo.get_comment(comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="삭제 권한이 없습니다.")
    await repo.delete_comment(comment)


# ── 신고 ─────────────────────────────────────────────────────────────────────

reports_router = APIRouter(prefix="/reports", tags=["reports"])


@reports_router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreateRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> dict[str, str]:
    try:
        await ReportRepository().create_report(
            reporter_id=current_user.id,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 신고한 대상입니다.") from err
    return {"message": "신고가 접수되었습니다."}


# ── 퀴즈 ─────────────────────────────────────────────────────────────────────

quiz_router = APIRouter(prefix="/quizzes", tags=["quiz"])

_QUIZ_ERRORS: dict[str, tuple[int, str]] = {
    "no_quiz_today": (status.HTTP_404_NOT_FOUND, "오늘의 퀴즈가 없습니다."),
    "already_answered": (status.HTTP_409_CONFLICT, "이미 답변한 퀴즈입니다."),
    "daily_limit_exceeded": (status.HTTP_429_TOO_MANY_REQUESTS, "일일 퀴즈 한도(5문제)를 초과했습니다."),
    "quiz_not_found": (status.HTTP_404_NOT_FOUND, "퀴즈를 찾을 수 없습니다."),
}


@quiz_router.get("/today")
async def get_today_quiz(current_user: User = Depends(get_request_user)) -> dict:  # noqa: B008
    try:
        data = await HealthQuizService().get_today_quiz(current_user.id)
    except ValueError as e:
        code, detail = _QUIZ_ERRORS.get(str(e), (status.HTTP_400_BAD_REQUEST, str(e)))
        raise HTTPException(status_code=code, detail=detail) from e
    quiz = data["quiz"]
    return {
        "quiz": QuizResponse.model_validate(quiz),
        "already_answered": data["already_answered"],
    }


@quiz_router.post("/{quiz_id}/answer", response_model=QuizAnswerResponse)
async def answer_quiz(
    quiz_id: int,
    body: QuizAnswerRequest,
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> QuizAnswerResponse:
    try:
        result = await HealthQuizService().answer_quiz(current_user.id, quiz_id, body.selected_option)
    except ValueError as e:
        code, detail = _QUIZ_ERRORS.get(str(e), (status.HTTP_400_BAD_REQUEST, str(e)))
        raise HTTPException(status_code=code, detail=detail) from e
    return QuizAnswerResponse(**result)


@quiz_router.get("/history", response_model=list[QuizAttemptHistoryItem])
async def get_quiz_history(
    page: int = Query(1, ge=1),  # noqa: B008
    size: int = Query(20, ge=1, le=100),  # noqa: B008
    current_user: User = Depends(get_request_user),  # noqa: B008
) -> list[QuizAttemptHistoryItem]:
    attempts, _ = await HealthQuizService().get_attempt_history(current_user.id, page, size)
    return [
        QuizAttemptHistoryItem(
            quiz_id=a.quiz_id,
            quiz_date=a.quiz.quiz_date,
            question=a.quiz.question,
            category=a.quiz.category,
            selected_option=a.selected_option,
            is_correct=a.is_correct,
            points_earned=a.points_earned,
            attempted_at=a.attempted_at,
        )
        for a in attempts
    ]
