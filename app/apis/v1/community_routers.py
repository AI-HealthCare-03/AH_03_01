from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.security import get_request_user
from app.dtos.community import PostCreateRequest, PostDetailResponse, PostListItem, PostListResponse, PostUpdateRequest
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
    post_id: int, body: PostUpdateRequest, current_user: User = Depends(get_request_user)  # noqa: B008
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