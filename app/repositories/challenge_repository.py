from __future__ import annotations

from datetime import date, datetime
from typing import Any

from tortoise.expressions import Q

from app.core import config
from app.models.challenge import (
    Challenge,
    ChallengeInvite,
    ChallengeParticipant,
    ChallengeReaction,
    ChallengeRecommendation,
    ChallengeStatus,
    ChallengeTemplate,
    ChallengeVerification,
    ChallengeVerificationAttachment,
    ImageVerificationJob,
    InviteStatus,
    ParticipantRole,
    ParticipantStatus,
    ReactionType,
    VerificationMethod,
    VerificationStatus,
)


class ChallengeTemplateRepository:
    def __init__(self) -> None:
        self._model = ChallengeTemplate

    async def list_active(self, category: str | None = None) -> list[ChallengeTemplate]:
        qs = self._model.filter(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return list(await qs.order_by("category", "id"))

    async def get(self, template_id: int) -> ChallengeTemplate | None:
        return await self._model.get_or_none(id=template_id, is_active=True)


class ChallengeRepository:
    def __init__(self) -> None:
        self._model = Challenge

    async def create(self, data: dict[str, Any]) -> Challenge:
        return await self._model.create(**data)

    async def get(self, challenge_id: int) -> Challenge | None:
        return await self._model.get_or_none(id=challenge_id, is_deleted=False)

    async def list(
        self,
        *,
        user_id: int | None = None,
        scope: str | None = None,
        status: str | None = None,
        category: str | None = None,
        visibility: str | None = None,
        keyword: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = None,  # "start_date" | "end_date" | None(기본: created_at)
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Challenge], int]:
        qs = self._model.filter(is_deleted=False)
        if scope is not None:
            qs = qs.filter(scope=scope)
        if status is not None:
            qs = qs.filter(status=status)
        if category is not None:
            qs = qs.filter(category=category)
        if visibility is not None:
            qs = qs.filter(visibility=visibility)
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
        if date_from is not None:
            qs = qs.filter(end_date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(start_date__lte=date_to)
        if user_id is not None:
            # Tortoise 가 __in= 에 subquery 객체를 직접 받지 못하므로 list 로 먼저 materialize.
            # PENDING 상태도 포함 — 초대 코드로 참가 신청 후 승인 대기 중인 챌린지도 목록에 표시
            participating_ids = await ChallengeParticipant.filter(
                user_id=user_id,
                status__in=[ParticipantStatus.APPROVED, ParticipantStatus.PENDING],
            ).values_list("challenge_id", flat=True)
            qs = qs.filter(Q(creator_id=user_id) | Q(id__in=list(participating_ids)))
        total = await qs.count()
        _order = {"start_date": "start_date", "end_date": "end_date"}.get(sort_by or "", "-created_at")
        items = await qs.order_by(_order).offset((page - 1) * size).limit(size)
        return list(items), total

    async def update_instance(self, challenge: Challenge, data: dict[str, Any]) -> Challenge:
        fields_updated = []
        for key, value in data.items():
            if value is not None:
                setattr(challenge, key, value)
                fields_updated.append(key)
        if fields_updated:
            await challenge.save(update_fields=fields_updated)
        return challenge

    async def soft_delete(self, challenge: Challenge) -> None:
        challenge.is_deleted = True
        challenge.status = ChallengeStatus.CANCELLED
        await challenge.save(update_fields=["is_deleted", "status"])


class ChallengeParticipantRepository:
    def __init__(self) -> None:
        self._model = ChallengeParticipant

    async def create(self, data: dict[str, Any]) -> ChallengeParticipant:
        return await self._model.create(**data)

    async def get(self, participant_id: int) -> ChallengeParticipant | None:
        return await self._model.get_or_none(id=participant_id)

    async def get_by_user(self, challenge_id: int, user_id: int) -> ChallengeParticipant | None:
        return await self._model.get_or_none(challenge_id=challenge_id, user_id=user_id)

    async def list_for_challenge(
        self,
        challenge_id: int,
        status: str | None = None,
    ) -> list[ChallengeParticipant]:
        qs = self._model.filter(challenge_id=challenge_id).prefetch_related("user")
        if status:
            qs = qs.filter(status=status)
        return list(await qs.order_by("joined_at"))

    async def count_active(self, challenge_id: int) -> int:
        return await self._model.filter(
            challenge_id=challenge_id,
            status=ParticipantStatus.APPROVED,
        ).count()

    async def update_status(
        self,
        participant: ChallengeParticipant,
        status: ParticipantStatus,
        *,
        leaving: bool = False,
    ) -> ChallengeParticipant:
        participant.status = status
        update_fields = ["status"]
        if leaving:
            participant.left_at = datetime.now(config.TIMEZONE)
            update_fields.append("left_at")
        await participant.save(update_fields=update_fields)
        return participant

    async def increment_missed(self, participant: ChallengeParticipant) -> ChallengeParticipant:
        participant.missed_count += 1
        await participant.save(update_fields=["missed_count"])
        return participant

    async def add_score(self, participant: ChallengeParticipant, points: int) -> ChallengeParticipant:
        participant.current_score += points
        await participant.save(update_fields=["current_score"])
        return participant

    async def has_owner(self, challenge_id: int) -> bool:
        return await self._model.filter(challenge_id=challenge_id, role=ParticipantRole.OWNER).exists()


class ChallengeInviteRepository:
    def __init__(self) -> None:
        self._model = ChallengeInvite

    async def create(self, data: dict[str, Any]) -> ChallengeInvite:
        return await self._model.create(**data)

    async def get(self, invite_id: int) -> ChallengeInvite | None:
        return await self._model.get_or_none(id=invite_id)

    async def get_by_code(self, invite_code: str) -> ChallengeInvite | None:
        return await self._model.get_or_none(invite_code=invite_code, status=InviteStatus.PENDING)

    async def list_for_invitee(
        self,
        invitee_id: Any,
        *,
        status_filter: InviteStatus | None = None,
    ) -> list[ChallengeInvite]:
        qs = self._model.filter(invitee_id=invitee_id)
        if status_filter is not None:
            qs = qs.filter(status=status_filter)
        return list(await qs.order_by("-created_at"))

    async def update_status(self, invite: ChallengeInvite, status: InviteStatus) -> ChallengeInvite:
        invite.status = status
        invite.responded_at = datetime.now(config.TIMEZONE)
        await invite.save(update_fields=["status", "responded_at"])
        return invite


class ChallengeVerificationRepository:
    def __init__(self) -> None:
        self._model = ChallengeVerification

    async def create(self, data: dict[str, Any]) -> ChallengeVerification:
        return await self._model.create(**data)

    async def get(self, verification_id: int) -> ChallengeVerification | None:
        return await self._model.get_or_none(id=verification_id, is_deleted=False)

    async def list(
        self,
        *,
        challenge_id: int | None = None,
        user_id: int | None = None,
        verified_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        method: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ChallengeVerification], int]:
        qs = self._model.filter(is_deleted=False)
        if challenge_id is not None:
            qs = qs.filter(challenge_id=challenge_id)
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        if verified_date is not None:
            qs = qs.filter(verified_date=verified_date)
        if date_from is not None:
            qs = qs.filter(verified_date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(verified_date__lte=date_to)
        if status:
            qs = qs.filter(status=status)
        if method:
            qs = qs.filter(method=method)
        total = await qs.count()
        items = await qs.order_by("-verified_date", "-created_at").offset((page - 1) * size).limit(size)
        return list(items), total

    async def update_status(
        self,
        verification: ChallengeVerification,
        status: VerificationStatus,
        reason: str | None = None,
    ) -> ChallengeVerification:
        verification.status = status
        update_fields = ["status"]
        if reason is not None:
            verification.rejection_reason = reason
            update_fields.append("rejection_reason")
        await verification.save(update_fields=update_fields)
        return verification

    async def soft_delete(self, verification: ChallengeVerification) -> None:
        verification.is_deleted = True
        await verification.save(update_fields=["is_deleted"])

    async def increment_counter(
        self,
        verification: ChallengeVerification,
        *,
        likes: int = 0,
        comments: int = 0,
    ) -> ChallengeVerification:
        verification.like_count = max(0, verification.like_count + likes)
        verification.comment_count = max(0, verification.comment_count + comments)
        await verification.save(update_fields=["like_count", "comment_count"])
        return verification

    async def list_feed(
        self,
        challenge_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ChallengeVerification], int]:
        qs = self._model.filter(challenge_id=challenge_id, is_deleted=False)
        total = await qs.count()
        items = await qs.prefetch_related("user").order_by("-created_at").offset((page - 1) * size).limit(size)
        return list(items), total

    async def aggregate_summary(
        self,
        user_id: int,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        qs = self._model.filter(user_id=user_id, is_deleted=False)
        if date_from is not None:
            qs = qs.filter(verified_date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(verified_date__lte=date_to)
        total = await qs.count()
        success = await qs.filter(status=VerificationStatus.APPROVED).count()
        pending = await qs.filter(status=VerificationStatus.PENDING).count()
        rejected = await qs.filter(status=VerificationStatus.REJECTED).count()
        per_challenge: dict[int, dict[str, Any]] = {}
        async for record in qs:
            entry = per_challenge.setdefault(
                record.challenge_id,
                {"challenge_id": record.challenge_id, "success": 0, "pending": 0, "rejected": 0, "total": 0},
            )
            entry["total"] += 1
            if record.status == VerificationStatus.APPROVED:
                entry["success"] += 1
            elif record.status == VerificationStatus.PENDING:
                entry["pending"] += 1
            elif record.status == VerificationStatus.REJECTED:
                entry["rejected"] += 1
        return {
            "total": total,
            "success_count": success,
            "fail_count": rejected,
            "pending_count": pending,
            "per_challenge": list(per_challenge.values()),
        }


class ImageVerificationJobRepository:
    def __init__(self) -> None:
        self._model = ImageVerificationJob

    async def create(self, data: dict[str, Any]) -> ImageVerificationJob:
        return await self._model.create(**data)

    async def get_for_verification(self, verification_id: int) -> ImageVerificationJob | None:
        return await self._model.filter(verification_id=verification_id).order_by("-queued_at").first()


class ChallengeVerificationAttachmentRepository:
    def __init__(self) -> None:
        self._model = ChallengeVerificationAttachment

    async def create_many(self, verification_id: int, file_ids: list[int]) -> list[ChallengeVerificationAttachment]:
        created: list[ChallengeVerificationAttachment] = []
        for index, file_id in enumerate(file_ids):
            instance = await self._model.create(
                verification_id=verification_id,
                file_id=file_id,
                sort_order=index,
            )
            created.append(instance)
        return created


class ChallengeReactionRepository:
    def __init__(self) -> None:
        self._model = ChallengeReaction

    async def create(self, data: dict[str, Any]) -> ChallengeReaction:
        return await self._model.create(**data)

    async def get(self, reaction_id: int) -> ChallengeReaction | None:
        return await self._model.get_or_none(id=reaction_id, is_deleted=False)

    async def get_existing_like(self, verification_id: int, user_id: int) -> ChallengeReaction | None:
        return await self._model.get_or_none(
            verification_id=verification_id,
            user_id=user_id,
            type=ReactionType.LIKE,
            is_deleted=False,
        )

    async def list_comments(self, verification_id: int) -> list[ChallengeReaction]:
        return list(
            await self._model.filter(
                verification_id=verification_id,
                type=ReactionType.COMMENT,
                is_deleted=False,
            ).order_by("created_at")
        )

    async def get_liked_verification_ids(self, user_id: int, verification_ids: list[int]) -> set[int]:
        if not verification_ids:
            return set()
        liked = await self._model.filter(
            user_id=user_id,
            verification_id__in=verification_ids,
            type=ReactionType.LIKE,
            is_deleted=False,
        ).values_list("verification_id", flat=True)
        return set(liked)

    async def list_comments_with_replies(self, verification_id: int) -> list[ChallengeReaction]:
        top_level = list(
            await self._model.filter(
                verification_id=verification_id,
                type=ReactionType.COMMENT,
                parent_id__isnull=True,
                is_deleted=False,
            )
            .prefetch_related("user")
            .order_by("created_at")
        )
        for comment in top_level:
            comment.reply_list = list(  # type: ignore[attr-defined]
                await self._model.filter(
                    parent_id=comment.id,
                    type=ReactionType.COMMENT,
                    is_deleted=False,
                )
                .prefetch_related("user")
                .order_by("created_at")
            )
        return top_level

    async def get_user_like(self, verification_id: int, user_id: int) -> ChallengeReaction | None:
        return await self._model.get_or_none(
            verification_id=verification_id,
            user_id=user_id,
            type=ReactionType.LIKE,
            is_deleted=False,
        )

    async def update_content(self, reaction: ChallengeReaction, content: str) -> ChallengeReaction:
        reaction.content = content
        await reaction.save(update_fields=["content"])
        return reaction

    async def soft_delete(self, reaction: ChallengeReaction) -> None:
        reaction.is_deleted = True
        await reaction.save(update_fields=["is_deleted"])


class ChallengeRecommendationRepository:
    def __init__(self) -> None:
        self._model = ChallengeRecommendation

    async def upsert(
        self,
        *,
        user_id: int,
        disease_risk_id: int | None,
        template_id: int | None,
        challenge_id: int | None,
        priority: str,
        reason: str,
    ) -> ChallengeRecommendation:
        existing = await self._model.filter(
            user_id=user_id,
            disease_risk_id=disease_risk_id,
            template_id=template_id,
        ).first()
        if existing is not None:
            existing.priority = priority  # type: ignore[assignment]
            existing.reason = reason
            existing.challenge_id = challenge_id
            await existing.save(update_fields=["priority", "reason", "challenge_id"])
            return existing
        return await self._model.create(
            user_id=user_id,
            disease_risk_id=disease_risk_id,
            template_id=template_id,
            challenge_id=challenge_id,
            priority=priority,
            reason=reason,
        )


def is_method_check_or_photo(method: str) -> bool:
    return method in {VerificationMethod.CHECK.value, VerificationMethod.PHOTO.value}
