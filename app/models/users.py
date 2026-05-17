from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class User(models.Model):
    """ERD 사양: docs/ERD v1.pdf USER 테이블.

    UUID PK 전환은 광범위 FK 영향이라 별도 마이그레이션으로 분리. 본 라운드는
    nickname 등 누락 칼럼만 우선 보강한다.
    """

    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=40)
    hashed_password = fields.CharField(max_length=128)
    nickname = fields.CharField(max_length=10, unique=True, null=True)  # ERD: NN, but null 허용해 기존 user 백필 안전
    name = fields.CharField(max_length=20)
    phone_number = fields.CharField(max_length=11)
    birthday = fields.DateField()
    gender = fields.CharEnumField(enum_type=Gender, max_length=10)
    avatar_file_id = fields.BigIntField(null=True)  # ERD 의 profile_file_id 대응
    social_provider = fields.CharField(max_length=20, null=True)
    social_id = fields.CharField(max_length=128, null=True)
    login_fail_count = fields.IntField(default=0)
    device_id = fields.CharField(max_length=128, null=True)
    refresh_token_hash = fields.CharField(max_length=255, null=True)
    last_login = fields.DatetimeField(null=True)  # ERD 의 last_login_at
    password_changed_at = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    is_deleted = fields.BooleanField(default=False)
    is_banned = fields.BooleanField(default=False)
    ban_reason = fields.TextField(null=True)
    banned_at = fields.DatetimeField(null=True)
    banned_by = fields.BigIntField(null=True)
    withdrawal_reason = fields.TextField(null=True)
    terms_agreed_at = fields.DatetimeField(null=True)
    privacy_agreed_at = fields.DatetimeField(null=True)
    deleted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
