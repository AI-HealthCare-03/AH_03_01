from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.dtos.base import BaseSerializerModel
from app.models.challenge import (
    ChallengeCadence,
    ChallengeCategory,
    ChallengeDifficulty,
    ChallengeScope,
    ChallengeStatus,
    ChallengeVisibility,
    ExerciseSubType,
    GoalType,
    InviteStatus,
    ParticipantRole,
    ParticipantStatus,
    ReactionType,
    RecommendationPriority,
    VerificationMethod,
    VerificationStatus,
    VerificationType,
)

# ---------------------------------------------------------------------------
# Template / Category browse
# ---------------------------------------------------------------------------


class TemplateGoalOption(BaseModel):
    label: str
    value: Decimal | int | str
    unit: str | None = None


class ChallengeTemplateResponse(BaseSerializerModel):
    id: int
    category: ChallengeCategory
    sub_category: ExerciseSubType | None
    title: str
    description: str | None
    goal_type: GoalType
    goal_value_options: list[Any]
    default_unit: str | None
    verification_type: VerificationType
    difficulty: ChallengeDifficulty


class ChallengeCategoryResponse(BaseModel):
    category: ChallengeCategory
    sub_categories: list[ExerciseSubType]
    templates: list[ChallengeTemplateResponse]


# ---------------------------------------------------------------------------
# Challenge CRUD
# ---------------------------------------------------------------------------


class ChallengeCreateRequest(BaseModel):
    title: Annotated[str, Field(min_length=2, max_length=120)]
    description: Annotated[str | None, Field(None, max_length=1000)] = None
    template_id: int | None = None
    category: ChallengeCategory
    sub_category: ExerciseSubType | None = None
    goal_type: GoalType
    goal_value: Annotated[Decimal | None, Field(None, ge=0)] = None
    unit: Annotated[str | None, Field(None, max_length=20)] = None
    cadence: ChallengeCadence = ChallengeCadence.DAILY
    # 카테고리별 자유 설정. 예시 키: weekly_target_count, group_target_count,
    # group_target_members, amount, duration_minutes, distance_km, step_count,
    # diet_type, sleep_mode, sleep_time_range, sleep_duration_hours, wake_time,
    # weight_loss_mode, weight_loss_kg, exercise_other_type, questionnaire_template
    goal_config: dict[str, Any] = Field(default_factory=dict)
    verification_type: VerificationType
    difficulty: ChallengeDifficulty = ChallengeDifficulty.LEVEL_1
    visibility: ChallengeVisibility = ChallengeVisibility.PUBLIC
    max_participants: Annotated[int, Field(ge=1, le=5)] = 1
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _validate_dates(self) -> "ChallengeCreateRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date 는 start_date 이상이어야 합니다.")
        return self

    @model_validator(mode="after")
    def _validate_group_goal(self) -> "ChallengeCreateRequest":
        if self.max_participants > 1:
            has_sum = isinstance(self.goal_config.get("group_target_count"), int)
            has_members = isinstance(self.goal_config.get("group_target_members"), int)
            if has_sum == has_members:
                raise ValueError(
                    "그룹 챌린지는 group_target_count 또는 group_target_members 중 하나를 양의 정수로 지정해야 합니다."
                )
        return self


class ChallengeUpdateRequest(BaseModel):
    title: Annotated[str | None, Field(None, min_length=2, max_length=120)] = None
    description: Annotated[str | None, Field(None, max_length=1000)] = None
    goal_value: Annotated[Decimal | None, Field(None, ge=0)] = None
    unit: Annotated[str | None, Field(None, max_length=20)] = None
    visibility: ChallengeVisibility | None = None
    end_date: date | None = None
    status: ChallengeStatus | None = None  # 방장만 CANCELLED 로 변경 가능 (포기)


class ChallengeResponse(BaseSerializerModel):
    id: int
    title: str
    description: str | None
    category: ChallengeCategory
    sub_category: ExerciseSubType | None
    scope: ChallengeScope
    goal_type: GoalType
    goal_value: Decimal | None
    unit: str | None
    verification_type: VerificationType
    difficulty: ChallengeDifficulty
    visibility: ChallengeVisibility
    status: ChallengeStatus
    max_participants: int
    start_date: date
    end_date: date
    creator_id: UUID | None
    created_at: datetime
    cadence: ChallengeCadence = ChallengeCadence.DAILY
    goal_config: dict[str, Any] = Field(default_factory=dict)
    invite_code: str | None = None  # 그룹 챌린지 + 방장/참여자에게만 노출
    is_member: bool = False  # 현재 사용자가 참여자/방장인지 여부
    my_progress: int | None = None  # 내 달성일 수 (승인된 인증 횟수)
    total_days: int | None = None   # 챌린지 전체 기간 일 수
    achievement_rate: int = 0       # 달성률 % (그룹: 전체 멤버 기준, 개인: 내 기준)


class ChallengeListItem(BaseModel):
    id: int
    title: str
    scope: ChallengeScope
    status: ChallengeStatus
    category: ChallengeCategory
    visibility: ChallengeVisibility = ChallengeVisibility.PUBLIC
    max_participants: int | None = None
    start_date: date
    end_date: date
    created_at: datetime
    # 스코프에 관계없이 항상 "내 개인 진행률" (my_progress ÷ total_days × 100)
    # 그룹 챌린지 전체 달성률은 achievement_rate 사용 — 두 필드를 혼용하지 않도록 주의
    my_progress_percent: float | None = None
    my_progress: int | None = None  # 내 달성일 수 (승인된 인증 횟수)
    total_days: int | None = None  # 챌린지 전체 기간 일 수
    achievement_rate: int = 0       # 달성률 % (그룹: 전체 멤버 평균, 개인: 내 기준)
    missed_count: int | None = None  # 누락 횟수
    my_participant_status: str | None = None  # 현재 사용자의 참여 상태 (APPROVED/LEFT 등)


class ChallengeListResponse(BaseModel):
    page: int
    size: int
    total_elements: int
    total_pages: int
    items: list[ChallengeListItem]


# ---------------------------------------------------------------------------
# Participants & invites
# ---------------------------------------------------------------------------


class ParticipantResponse(BaseSerializerModel):
    id: int
    challenge_id: int
    user_id: UUID
    role: ParticipantRole
    status: ParticipantStatus
    current_score: int
    joined_at: datetime
    progress_days: int = 0   # 승인된 인증 횟수
    achievement_rate: int = 0  # 개인 달성률 %


class JoinByCodeRequest(BaseModel):
    invite_code: Annotated[str, Field(min_length=4, max_length=12)]


class InviteCreateResponse(BaseModel):
    invite_code: str
    expires_at: datetime | None
    invite_id: int


class DirectInviteRequest(BaseModel):
    invitee_id: UUID


class InvitationResponse(BaseSerializerModel):
    id: int
    challenge_id: int
    invitee_id: UUID | None
    invite_code: str | None
    status: InviteStatus
    expires_at: datetime | None
    created_at: datetime


class InvitationActionResponse(BaseModel):
    id: int
    status: InviteStatus
    responded_at: datetime | None


# ---------------------------------------------------------------------------
# Verifications
# ---------------------------------------------------------------------------


class VerificationCreateRequest(BaseModel):
    challenge_id: int
    method: VerificationMethod = VerificationMethod.CHECK
    verified_date: date
    checked: bool | None = None
    answers: dict[str, Any] | None = None
    photo_file_id: int | None = None
    shield_inventory_id: int | None = None
    caption: Annotated[str | None, Field(None, max_length=500)] = None
    duration_seconds: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> "VerificationCreateRequest":
        if self.method == VerificationMethod.CHECK and self.checked is None:
            raise ValueError("CHECK 인증은 checked 값이 필요합니다.")
        if self.method == VerificationMethod.PHOTO and self.photo_file_id is None:
            raise ValueError("PHOTO 인증은 photo_file_id 가 필요합니다.")
        if self.method == VerificationMethod.SHIELD and self.shield_inventory_id is None:
            raise ValueError("SHIELD 인증은 shield_inventory_id 가 필요합니다.")
        return self


class VerificationUpdateRequest(BaseModel):
    status: VerificationStatus | None = None
    rejection_reason: Annotated[str | None, Field(None, max_length=500)] = None


class VerificationResponse(BaseSerializerModel):
    id: int
    challenge_id: int
    user_id: UUID
    method: VerificationMethod
    verified_date: date
    checked: bool | None
    photo_file_id: int | None
    status: VerificationStatus
    caption: str | None
    verified_duration_seconds: int | None
    rejection_reason: str | None
    like_count: int
    comment_count: int
    created_at: datetime


class VerificationListResponse(BaseModel):
    page: int
    size: int
    total_elements: int
    total_pages: int
    items: list[VerificationResponse]


class VerificationFeedItem(BaseModel):
    id: int
    user_id: UUID
    user_nickname: str | None
    method: VerificationMethod
    verified_date: date
    caption: str | None
    photo_file_id: int | None
    verified_duration_seconds: int | None
    like_count: int
    comment_count: int
    my_like: bool
    created_at: datetime


class VerificationFeedResponse(BaseModel):
    page: int
    size: int
    total_elements: int
    total_pages: int
    items: list[VerificationFeedItem]


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------


class ReactionCreateRequest(BaseModel):
    type: ReactionType
    content: Annotated[str | None, Field(None, max_length=500)] = None

    @model_validator(mode="after")
    def _validate(self) -> "ReactionCreateRequest":
        if self.type == ReactionType.COMMENT and not self.content:
            raise ValueError("댓글은 content 가 필요합니다.")
        return self


class ReactionUpdateRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=500)]


class ReactionResponse(BaseSerializerModel):
    id: int
    user_id: UUID
    type: ReactionType
    content: str | None
    parent_id: int | None
    created_at: datetime


class ReactionWithReplies(ReactionResponse):
    replies: list[ReactionResponse] = []


class ReactionListResponse(BaseModel):
    like_count: int
    my_like: bool
    comments: list[ReactionWithReplies]


# ---------------------------------------------------------------------------
# Summary & Recommendation
# ---------------------------------------------------------------------------


class ChallengeSummaryResponse(BaseModel):
    period: str
    from_date: date | None
    to_date: date | None
    total: int
    success_count: int
    fail_count: int
    pending_count: int
    rewards_estimated: int
    per_challenge: list[dict[str, Any]]


class ChallengeRecommendationItem(BaseModel):
    template_id: int | None
    challenge_id: int | None
    category: ChallengeCategory
    sub_category: ExerciseSubType | None
    title: str
    priority: RecommendationPriority
    reason: str | None
    already_joined: bool = False


class ChallengeRecommendationResponse(BaseModel):
    prediction_id: int | None
    items: list[ChallengeRecommendationItem]
    disclaimer: str = "본 추천은 의학적 진단이 아닌 참고용 위험도 지표를 기반으로 생성되었습니다."
