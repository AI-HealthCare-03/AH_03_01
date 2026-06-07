from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class PostCategory(StrEnum):
    NOTICE = "NOTICE"
    INFO = "INFO"
    FREE = "FREE"


class Post(models.Model):
    id = fields.BigIntField(primary_key=True)
    title = fields.CharField(max_length=200)
    content = fields.TextField()
    category = fields.CharEnumField(PostCategory, max_length=20)
    is_pinned = fields.BooleanField(default=False)
    view_count = fields.IntField(default=0)
    author: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="posts", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "community_posts"
        ordering = ["-is_pinned", "-created_at"]
