from enum import StrEnum
from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.health import DiseaseRisk
    from app.models.users import User


class ChallengeCategory(StrEnum):
    EXERCISE = "EXERCISE"
    WATER = "WATER"
    SLEEP = "SLEEP"
    DIET = "DIET"
    NO_SMOKING = "NO_SMOKING"
    NO_ALCOHOL = "NO_ALCOHOL"
    DISEASE_CARE = "DISEASE_CARE"
    MEDITATION = "MEDITATION"
    WEIGHT_MANAGEMENT = "WEIGHT_MANAGEMENT"


class ExerciseSubType(StrEnum):
    WALKING = "WALKING"
    RUNNING = "RUNNING"
    STRENGTH = "STRENGTH"
    CYCLING = "CYCLING"
    SWIMMING = "SWIMMING"
    OTHER = "OTHER"


class GoalType(StrEnum):
    DURATION = "DURATION"
    COUNT = "COUNT"
    AMOUNT = "AMOUNT"
    CHECK = "CHECK"


class VerificationType(StrEnum):
    CHECK = "CHECK"
    PHOTO = "PHOTO"


class ChallengeCadence(StrEnum):
    """챌린지 인정 빈도 정책.

    DAILY: 매일 인증형 (데일리 보상 + 기간 보상)
    WEEKLY_COUNT: 1주일 동안 목표 횟수 (기간 보상만)
    GROUP_SUM: 그룹 합산 횟수 도달
    GROUP_MEMBERS: 그룹 달성 인원 도달 (체중/금연/금주)
    """

    DAILY = "DAILY"
    WEEKLY_COUNT = "WEEKLY_COUNT"
    GROUP_SUM = "GROUP_SUM"
    GROUP_MEMBERS = "GROUP_MEMBERS"


class ChallengeScope(StrEnum):
    PERSONAL = "PERSONAL"
    GROUP = "GROUP"


class ChallengeStatus(StrEnum):
    RECRUITING = "RECRUITING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ChallengeDifficulty(StrEnum):
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    LEVEL_4 = "LEVEL_4"


class ChallengeVisibility(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class ParticipantRole(StrEnum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"


class ParticipantStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LEFT = "LEFT"
    KICKED = "KICKED"


class InviteType(StrEnum):
    CODE = "CODE"
    DIRECT = "DIRECT"


class InviteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VerificationMethod(StrEnum):
    CHECK = "CHECK"
    PHOTO = "PHOTO"
    SHIELD = "SHIELD"  # 실패 방지권


class VerificationJobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ReactionType(StrEnum):
    LIKE = "LIKE"
    COMMENT = "COMMENT"


class RecommendationPriority(StrEnum):
    TOP = "TOP"
    RECOMMENDED = "RECOMMENDED"
    OPTIONAL = "OPTIONAL"


class ChallengeTemplate(models.Model):
    id = fields.BigIntField(primary_key=True)
    category = fields.CharEnumField(enum_type=ChallengeCategory)
    sub_category = fields.CharEnumField(enum_type=ExerciseSubType, null=True)
    title = fields.CharField(max_length=80)
    description = fields.TextField(null=True)
    goal_type = fields.CharEnumField(enum_type=GoalType)
    goal_value_options: list[Any] = fields.JSONField(default=list)  # type: ignore[assignment]
    default_unit = fields.CharField(max_length=20, null=True)
    verification_type = fields.CharEnumField(enum_type=VerificationType)
    difficulty = fields.CharEnumField(enum_type=ChallengeDifficulty, default=ChallengeDifficulty.LEVEL_1)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "challenge_templates"
        indexes = [("category", "is_active")]


class Challenge(models.Model):
    id = fields.BigIntField(primary_key=True)
    template: fields.ForeignKeyNullableRelation["ChallengeTemplate"] = fields.ForeignKeyField(
        "models.ChallengeTemplate",
        related_name="challenges",
        null=True,
        on_delete=fields.SET_NULL,
    )
    template_id: int | None
    creator: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="created_challenges", on_delete=fields.CASCADE
    )
    creator_id: int
    title = fields.CharField(max_length=120)
    description = fields.TextField(null=True)
    category = fields.CharEnumField(enum_type=ChallengeCategory)
    sub_category = fields.CharEnumField(enum_type=ExerciseSubType, null=True)
    scope = fields.CharEnumField(enum_type=ChallengeScope, default=ChallengeScope.PERSONAL)
    goal_type = fields.CharEnumField(enum_type=GoalType)
    goal_value = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    unit = fields.CharField(max_length=20, null=True)
    cadence = fields.CharEnumField(enum_type=ChallengeCadence, default=ChallengeCadence.DAILY)
    # 카테고리별 자유 설정 (목표 수치/시간/식단종류/그룹 합산수/달성 인원 등)
    goal_config: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    verification_type = fields.CharEnumField(enum_type=VerificationType)
    difficulty = fields.CharEnumField(enum_type=ChallengeDifficulty, default=ChallengeDifficulty.LEVEL_1)
    visibility = fields.CharEnumField(enum_type=ChallengeVisibility, default=ChallengeVisibility.PUBLIC)
    status = fields.CharEnumField(enum_type=ChallengeStatus, default=ChallengeStatus.RECRUITING)
    max_participants = fields.IntField(default=1)
    start_date = fields.DateField()
    end_date = fields.DateField()
    is_deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "challenges"
        indexes = [("status", "scope"), ("creator_id", "status"), ("start_date", "end_date")]


class ChallengeParticipant(models.Model):
    id = fields.BigIntField(primary_key=True)
    challenge: fields.ForeignKeyRelation["Challenge"] = fields.ForeignKeyField(
        "models.Challenge", related_name="participants", on_delete=fields.CASCADE
    )
    challenge_id: int
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="challenge_participations", on_delete=fields.CASCADE
    )
    user_id: int
    role = fields.CharEnumField(enum_type=ParticipantRole, default=ParticipantRole.MEMBER)
    status = fields.CharEnumField(enum_type=ParticipantStatus, default=ParticipantStatus.APPROVED)
    current_score = fields.IntField(default=0)
    missed_count = fields.IntField(default=0)
    joined_at = fields.DatetimeField(auto_now_add=True)
    left_at = fields.DatetimeField(null=True)

    class Meta:
        table = "challenge_participants"
        unique_together = (("challenge", "user"),)
        indexes = [("challenge_id", "status"), ("user_id", "status")]


class ChallengeInvite(models.Model):
    id = fields.BigIntField(primary_key=True)
    challenge: fields.ForeignKeyRelation["Challenge"] = fields.ForeignKeyField(
        "models.Challenge", related_name="invites", on_delete=fields.CASCADE
    )
    challenge_id: int
    inviter: fields.ForeignKeyNullableRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="sent_invites", null=True, on_delete=fields.SET_NULL
    )
    invitee: fields.ForeignKeyNullableRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="received_invites", null=True, on_delete=fields.SET_NULL
    )
    invitee_id: int | None
    invite_code = fields.CharField(max_length=12, null=True)
    invite_type = fields.CharEnumField(enum_type=InviteType, default=InviteType.CODE)
    status = fields.CharEnumField(enum_type=InviteStatus, default=InviteStatus.PENDING)
    expires_at = fields.DatetimeField(null=True)
    responded_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_invites"
        indexes = [("invite_code",), ("invitee_id", "status")]


class ChallengeVerification(models.Model):
    id = fields.BigIntField(primary_key=True)
    challenge: fields.ForeignKeyRelation["Challenge"] = fields.ForeignKeyField(
        "models.Challenge", related_name="verifications", on_delete=fields.CASCADE
    )
    challenge_id: int
    participant: fields.ForeignKeyRelation["ChallengeParticipant"] = fields.ForeignKeyField(
        "models.ChallengeParticipant",
        related_name="verifications",
        on_delete=fields.CASCADE,
    )
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="challenge_verifications", on_delete=fields.CASCADE
    )
    user_id: int
    method = fields.CharEnumField(enum_type=VerificationMethod)
    verified_date = fields.DateField()
    checked = fields.BooleanField(null=True)
    answers: dict[str, Any] | None = fields.JSONField(default=dict, null=True)  # type: ignore[assignment]
    photo_file_id = fields.BigIntField(null=True)
    shield_inventory_id = fields.BigIntField(null=True)
    status = fields.CharEnumField(enum_type=VerificationStatus, default=VerificationStatus.PENDING)
    caption = fields.TextField(null=True)
    verified_duration_seconds = fields.IntField(null=True)
    rejection_reason = fields.TextField(null=True)
    like_count = fields.IntField(default=0)
    comment_count = fields.IntField(default=0)
    is_deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "challenge_verifications"
        unique_together = (("participant", "verified_date", "method"),)
        indexes = [("challenge_id", "verified_date"), ("user_id", "verified_date")]


class ImageVerificationJob(models.Model):
    id = fields.BigIntField(primary_key=True)
    verification: fields.ForeignKeyRelation["ChallengeVerification"] = fields.ForeignKeyField(
        "models.ChallengeVerification",
        related_name="image_jobs",
        on_delete=fields.CASCADE,
    )
    verification_id: int
    status = fields.CharEnumField(enum_type=VerificationJobStatus, default=VerificationJobStatus.QUEUED)
    result: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    model_version = fields.CharField(max_length=40, default="siglip2-stub-v0")
    error_message = fields.TextField(null=True)
    queued_at = fields.DatetimeField(auto_now_add=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "image_verification_jobs"
        indexes = [("status", "queued_at")]


class ChallengeVerificationAttachment(models.Model):
    id = fields.BigIntField(primary_key=True)
    verification: fields.ForeignKeyRelation["ChallengeVerification"] = fields.ForeignKeyField(
        "models.ChallengeVerification",
        related_name="attachments",
        on_delete=fields.CASCADE,
    )
    verification_id: int
    file_id = fields.BigIntField()
    sort_order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_verification_attachments"
        indexes = [("verification_id", "sort_order")]


class ChallengeReaction(models.Model):
    id = fields.BigIntField(primary_key=True)
    verification: fields.ForeignKeyRelation["ChallengeVerification"] = fields.ForeignKeyField(
        "models.ChallengeVerification",
        related_name="reactions",
        on_delete=fields.CASCADE,
    )
    verification_id: int
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="challenge_reactions", on_delete=fields.CASCADE
    )
    user_id: int
    type = fields.CharEnumField(enum_type=ReactionType)
    content = fields.TextField(null=True)
    is_deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "challenge_reactions"
        indexes = [("verification_id", "type"), ("user_id", "type")]


class ChallengeRecommendation(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="challenge_recommendations", on_delete=fields.CASCADE
    )
    user_id: int
    disease_risk: fields.ForeignKeyNullableRelation["DiseaseRisk"] = fields.ForeignKeyField(
        "models.DiseaseRisk",
        related_name="recommendations",
        null=True,
        on_delete=fields.SET_NULL,
    )
    disease_risk_id: int | None
    template: fields.ForeignKeyNullableRelation["ChallengeTemplate"] = fields.ForeignKeyField(
        "models.ChallengeTemplate",
        related_name="recommendations",
        null=True,
        on_delete=fields.SET_NULL,
    )
    template_id: int | None
    challenge: fields.ForeignKeyNullableRelation["Challenge"] = fields.ForeignKeyField(
        "models.Challenge",
        related_name="recommendations",
        null=True,
        on_delete=fields.SET_NULL,
    )
    challenge_id: int | None
    priority = fields.CharEnumField(enum_type=RecommendationPriority, default=RecommendationPriority.RECOMMENDED)
    reason = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_recommendations"
        indexes = [("user_id", "priority", "created_at")]
