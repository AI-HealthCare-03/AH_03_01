from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class User(models.Model):
    """ERD 사양: docs/ERD v1.pdf USER 테이블 (PK: UUID)."""

    id = fields.UUIDField(primary_key=True)
    # 소셜(카카오) 계정은 이메일을 수집하지 않는다(카카오가 본인인증 대행, 복구=카카오 재로그인).
    # 일반 가입 계정만 이메일을 가진다 → null 허용. 앱 레벨에서 일반 가입 시 중복/형식 검증.
    email = fields.CharField(max_length=40, null=True)
    hashed_password = fields.CharField(max_length=128)
    nickname = fields.CharField(max_length=10, unique=True, null=True)
    name = fields.CharField(max_length=20)
    phone_number = fields.CharField(max_length=11)
    birthday = fields.DateField()
    gender = fields.CharEnumField(enum_type=Gender, max_length=10)
    avatar_file_id = fields.BigIntField(null=True)
    social_provider = fields.CharField(max_length=20, null=True)
    social_id = fields.CharField(max_length=128, null=True)
    login_fail_count = fields.IntField(default=0)
    device_id = fields.CharField(max_length=128, null=True)
    fcm_token = fields.CharField(max_length=256, null=True)
    refresh_token_hash = fields.CharField(max_length=255, null=True)
    last_login = fields.DatetimeField(null=True)
    password_changed_at = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    is_deleted = fields.BooleanField(default=False)
    is_banned = fields.BooleanField(default=False)
    ban_reason = fields.TextField(null=True)
    banned_at = fields.DatetimeField(null=True)
    banned_by = fields.UUIDField(null=True)  # ERD: uuid
    withdrawal_reason = fields.TextField(null=True)
    terms_agreed_at = fields.DatetimeField(null=True)
    privacy_agreed_at = fields.DatetimeField(null=True)
    deleted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
