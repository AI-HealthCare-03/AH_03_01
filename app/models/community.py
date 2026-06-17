from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class ReportTargetType(StrEnum):
    POST = "POST"
    COMMENT = "COMMENT"
    VERIFICATION = "VERIFICATION"
    CHALLENGE_PARTICIPANT = "CHALLENGE_PARTICIPANT"


class ReportReason(StrEnum):
    ABUSE = "ABUSE"
    MISINFORMATION = "MISINFORMATION"
    PRIVACY = "PRIVACY"
    AD = "AD"
    FRAUD = "FRAUD"
    ETC = "ETC"


class PostCategory(StrEnum):
    NOTICE = "NOTICE"
    INFO = "INFO"
    FREE = "FREE"


class InfoCategory(StrEnum):
    HYPERTENSION = "HYPERTENSION"
    DIABETES = "DIABETES"
    CARDIOVASCULAR = "CARDIOVASCULAR"
    LIFESTYLE = "LIFESTYLE"


class Post(models.Model):
    id = fields.BigIntField(primary_key=True)
    title = fields.CharField(max_length=200)
    content = fields.TextField()
    category = fields.CharEnumField(PostCategory, max_length=20)
    info_category = fields.CharEnumField(InfoCategory, max_length=20, null=True)
    is_pinned = fields.BooleanField(default=False)
    is_deleted = fields.BooleanField(default=False)
    view_count = fields.IntField(default=0)
    author: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="posts", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "community_posts"
        ordering = ["-is_pinned", "-created_at"]


class Comment(models.Model):
    id = fields.BigIntField(primary_key=True)
    content = fields.TextField()
    post: fields.ForeignKeyRelation["Post"] = fields.ForeignKeyField(
        "models.Post", related_name="comments", on_delete=fields.CASCADE
    )
    author: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="comments", on_delete=fields.CASCADE
    )
    parent: fields.ForeignKeyNullableRelation["Comment"] = fields.ForeignKeyField(
        "models.Comment", related_name="replies", on_delete=fields.CASCADE, null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "community_comments"
        ordering = ["created_at"]


class Report(models.Model):
    id = fields.BigIntField(primary_key=True)
    target_type = fields.CharEnumField(ReportTargetType, max_length=30)
    target_id = fields.BigIntField()
    reason = fields.CharEnumField(ReportReason, max_length=20)
    reporter: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="reports", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "community_reports"
        unique_together = (("reporter", "target_type", "target_id"),)


class QuizCategory(StrEnum):
    BLOOD_SUGAR = "BLOOD_SUGAR"
    BLOOD_PRESSURE = "BLOOD_PRESSURE"
    DIET = "DIET"
    EXERCISE = "EXERCISE"
    GENERAL = "GENERAL"


class QuizOption(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class HealthQuiz(models.Model):
    id = fields.BigIntField(primary_key=True)
    question = fields.TextField()
    option_a = fields.CharField(max_length=200)
    option_b = fields.CharField(max_length=200)
    option_c = fields.CharField(max_length=200)
    option_d = fields.CharField(max_length=200)
    correct_option = fields.CharEnumField(QuizOption, max_length=1)
    explanation = fields.TextField()
    category = fields.CharEnumField(QuizCategory, max_length=20, default=QuizCategory.GENERAL)
    quiz_date = fields.DateField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "health_quizzes"
        ordering = ["id"]


class QuizAttempt(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="quiz_attempts", on_delete=fields.CASCADE
    )
    quiz: fields.ForeignKeyRelation["HealthQuiz"] = fields.ForeignKeyField(
        "models.HealthQuiz", related_name="attempts", on_delete=fields.CASCADE
    )
    selected_option = fields.CharEnumField(QuizOption, max_length=1)
    is_correct = fields.BooleanField()
    points_earned = fields.IntField(default=0)
    attempted_at = fields.DatetimeField(auto_now_add=True)
    attempted_date = fields.DateField()  # Seoul 기준 날짜, 일일 중복 방지 인덱스 키

    class Meta:
        table = "quiz_attempts"
        unique_together = (("user", "quiz", "attempted_date"),)


class PostLike(models.Model):
    id = fields.BigIntField(primary_key=True)
    post: fields.ForeignKeyRelation["Post"] = fields.ForeignKeyField(
        "models.Post", related_name="likes", on_delete=fields.CASCADE
    )
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="post_likes", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "community_post_likes"
        unique_together = (("post", "user"),)


class CommentLike(models.Model):
    id = fields.BigIntField(primary_key=True)
    comment: fields.ForeignKeyRelation["Comment"] = fields.ForeignKeyField(
        "models.Comment", related_name="likes", on_delete=fields.CASCADE
    )
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="comment_likes", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "community_comment_likes"
        unique_together = (("comment", "user"),)


class DailyQuizAssignment(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="daily_quiz_assignments", on_delete=fields.CASCADE
    )
    quiz: fields.ForeignKeyRelation["HealthQuiz"] = fields.ForeignKeyField(
        "models.HealthQuiz", related_name="daily_assignments", on_delete=fields.CASCADE
    )
    assigned_date = fields.DateField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "daily_quiz_assignments"
        unique_together = (("user", "quiz", "assigned_date"),)
