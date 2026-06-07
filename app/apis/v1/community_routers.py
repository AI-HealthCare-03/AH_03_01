from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.security import get_request_user
from app.dtos.community import PostDetailResponse, PostListItem, PostListResponse
from app.models.community import Post, PostCategory
from app.models.users import User
from app.repositories.community_repository import PostRepository

posts_router = APIRouter(prefix="/posts", tags=["community"])


def _to_item(p: Post) -> PostListItem:
    return PostListItem(
        id=p.id, title=p.title, category=p.category, is_pinned=p.is_pinned,
        view_count=p.view_count, author_id=p.author_id,
        author_nickname=p.author.nickname, created_at=p.created_at,
    )


@posts_router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: PostCategory | None = Query(None),
    _: User = Depends(get_request_user),
) -> PostListResponse:
    posts, total = await PostRepository().list_posts(page, size, category)
    return PostListResponse(items=[_to_item(p) for p in posts], total=total, page=page, size=size)


@posts_router.get("/{post_id}", response_model=PostDetailResponse)
async def get_post(post_id: int, _: User = Depends(get_request_user)) -> PostDetailResponse:
    repo = PostRepository()
    post = await repo.get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    await repo.increment_view(post.id, post.view_count)
    return PostDetailResponse(**_to_item(post).model_dump(), content=post.content, updated_at=post.updated_at)
