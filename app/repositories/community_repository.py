from __future__ import annotations

from datetime import date
from uuid import UUID

from tortoise.functions import Count

from app.models.community import (
    Comment,
    CommentLike,
    HealthQuiz,
    Post,
    PostCategory,
    PostLike,
    QuizAttempt,
    QuizOption,
    Report,
    ReportReason,
    ReportTargetType,
)


class LikeRepository:
    async def get_post_like_count(self, post_id: int) -> int:
        return await PostLike.filter(post_id=post_id).count()

    async def is_post_liked(self, post_id: int, user_id: UUID) -> bool:
        return await PostLike.filter(post_id=post_id, user_id=user_id).exists()

    async def like_post(self, post_id: int, user_id: UUID) -> None:
        await PostLike.get_or_create(post_id=post_id, user_id=user_id)

    async def unlike_post(self, post_id: int, user_id: UUID) -> None:
        await PostLike.filter(post_id=post_id, user_id=user_id).delete()

    async def get_comment_like_count(self, comment_id: int) -> int:
        return await CommentLike.filter(comment_id=comment_id).count()

    async def is_comment_liked(self, comment_id: int, user_id: UUID) -> bool:
        return await CommentLike.filter(comment_id=comment_id, user_id=user_id).exists()

    async def like_comment(self, comment_id: int, user_id: UUID) -> None:
        await CommentLike.get_or_create(comment_id=comment_id, user_id=user_id)

    async def unlike_comment(self, comment_id: int, user_id: UUID) -> None:
        await CommentLike.filter(comment_id=comment_id, user_id=user_id).delete()


class PostRepository:
    async def list_posts(
        self, page: int = 1, size: int = 20, category: PostCategory | None = None
    ) -> tuple[list[Post], int]:
        qs = Post.all().prefetch_related("author").annotate(comment_count=Count("comments"))
        if category:
            qs = qs.filter(category=category)
        total = await qs.count()
        return list(await qs.offset((page - 1) * size).limit(size)), total

    async def get_post(self, post_id: int) -> Post | None:
        return await Post.get_or_none(id=post_id).prefetch_related("author").annotate(comment_count=Count("comments"))

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


class CommentRepository:
    async def list_comments(self, post_id: int) -> list[Comment]:
        return list(
            await Comment.filter(post_id=post_id, parent_id=None).prefetch_related("author").order_by("created_at")
        )

    async def list_replies(self, parent_id: int) -> list[Comment]:
        return list(await Comment.filter(parent_id=parent_id).prefetch_related("author").order_by("created_at"))

    async def get_comment(self, comment_id: int) -> Comment | None:
        return await Comment.get_or_none(id=comment_id).prefetch_related("author")

    async def create_comment(self, post_id: int, author_id: UUID, content: str, parent_id: int | None) -> Comment:
        comment = await Comment.create(post_id=post_id, author_id=author_id, content=content, parent_id=parent_id)
        return await Comment.get(id=comment.id).prefetch_related("author")

    async def update_comment(self, comment: Comment, content: str) -> Comment:
        comment.content = content
        await comment.save()
        return comment

    async def delete_comment(self, comment: Comment) -> None:
        await comment.delete()


class ReportRepository:
    async def create_report(
        self, reporter_id: UUID, target_type: ReportTargetType, target_id: int, reason: ReportReason
    ) -> Report:
        report, created = await Report.get_or_create(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            defaults={"reason": reason},
        )
        if not created:
            raise ValueError("already_reported")
        return report


class QuizRepository:
    async def get_quiz_by_date(self, quiz_date: date) -> HealthQuiz | None:
        return await HealthQuiz.get_or_none(quiz_date=quiz_date, is_active=True)

    async def get_quiz_by_id(self, quiz_id: int) -> HealthQuiz | None:
        return await HealthQuiz.get_or_none(id=quiz_id, is_active=True)

    async def list_unanswered_quizzes(self, user_id: UUID, limit: int) -> list[HealthQuiz]:
        attempted_ids = await QuizAttempt.filter(user_id=user_id).values_list("quiz_id", flat=True)
        return list(
            await HealthQuiz.filter(is_active=True, quiz_date__lte=date.today())
            .exclude(id__in=list(attempted_ids))
            .order_by("-quiz_date")
            .limit(limit)
        )

    async def get_attempt(self, user_id: UUID, quiz_id: int) -> QuizAttempt | None:
        return await QuizAttempt.get_or_none(user_id=user_id, quiz_id=quiz_id)

    async def create_attempt(
        self, user_id: UUID, quiz_id: int, selected_option: QuizOption, is_correct: bool, points_earned: int
    ) -> QuizAttempt:
        return await QuizAttempt.create(
            user_id=user_id,
            quiz_id=quiz_id,
            selected_option=selected_option,
            is_correct=is_correct,
            points_earned=points_earned,
        )

    async def list_attempts(self, user_id: UUID, page: int = 1, size: int = 20) -> tuple[list[QuizAttempt], int]:
        qs = QuizAttempt.filter(user_id=user_id).prefetch_related("quiz").order_by("-attempted_at")
        total = await qs.count()
        return list(await qs.offset((page - 1) * size).limit(size)), total
