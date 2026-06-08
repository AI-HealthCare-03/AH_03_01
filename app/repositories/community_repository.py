from __future__ import annotations

from uuid import UUID

from app.models.community import Post, PostCategory


class PostRepository:
    async def list_posts(
        self, page: int = 1, size: int = 20, category: PostCategory | None = None
    ) -> tuple[list[Post], int]:
        qs = Post.all().prefetch_related("author")
        if category:
            qs = qs.filter(category=category)
        total = await qs.count()
        return list(await qs.offset((page - 1) * size).limit(size)), total

    async def get_post(self, post_id: int) -> Post | None:
        return await Post.get_or_none(id=post_id).prefetch_related("author")

    async def increment_view(self, post_id: int, current: int) -> None:
        await Post.filter(id=post_id).update(view_count=current + 1)

    async def create_post(self, author_id: UUID, title: str, content: str, category: PostCategory) -> Post:
        return await Post.create(author_id=author_id, title=title, content=content, category=category)

    async def update_post(
        self, post: Post, title: str | None, content: str | None, category: PostCategory | None
    ) -> Post:
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        if category is not None:
            post.category = category
        await post.save()
        return post

    async def delete_post(self, post: Post) -> None:
        await post.delete()
