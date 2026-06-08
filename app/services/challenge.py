from __future__ import annotations

import math
import secrets
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.challenge import (
    ChallengeCreateRequest,
    ChallengeUpdateRequest,
    DirectInviteRequest,
    ReactionCreateRequest,
    ReactionUpdateRequest,
    VerificationCreateRequest,
    VerificationUpdateRequest,
)
from app.models.challenge import (
    Challenge,
    ChallengeCategory,
    ChallengeInvite,
    ChallengeParticipant,
    ChallengeReaction,
    ChallengeScope,
    ChallengeStatus,
    ChallengeTemplate,
    ChallengeVerification,
    InviteStatus,
    InviteType,
    ParticipantRole,
    ParticipantStatus,
    ReactionType,
    VerificationJobStatus,
    VerificationMethod,
    VerificationStatus,
    VerificationType,
)
from app.models.health import DiseaseRisk
from app.models.pet import GrowthEventSource
from app.models.users import User
from app.repositories.challenge_repository import (
    ChallengeInviteRepository,
    ChallengeParticipantRepository,
    ChallengeReactionRepository,
    ChallengeRecommendationRepository,
    ChallengeRepository,
    ChallengeTemplateRepository,
    ChallengeVerificationAttachmentRepository,
    ChallengeVerificationRepository,
    ImageVerificationJobRepository,
)
from app.services.ml import ChallengeRecommender, ImageVerifier
from app.services.pet import (
    XP_FROM_CHALLENGE_VERIFICATION,
    PetService,
    RescueTicketService,
)
from app.services.rewards import RewardService

MAX_MISSED_BEFORE_KICK = 3
INVITE_TTL = timedelta(days=7)


class ChallengeTemplateService:
    def __init__(self) -> None:
        self.repo = ChallengeTemplateRepository()

    async def list_active(self, category: str | None = None) -> list[ChallengeTemplate]:
        return await self.repo.list_active(category)


class ChallengeService:
    def __init__(self) -> None:
        self.repo = ChallengeRepository()
        self.template_repo = ChallengeTemplateRepository()
        self.participant_repo = ChallengeParticipantRepository()
        self.invite_repo = ChallengeInviteRepository()

    async def create(self, user: User, data: ChallengeCreateRequest) -> Challenge:
        scope = ChallengeScope.GROUP if data.max_participants > 1 else ChallengeScope.PERSONAL
        template = await self.template_repo.get(data.template_id) if data.template_id else None
        if data.template_id and template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="템플릿을 찾을 수 없습니다.")

        async with in_transaction():
            challenge = await self.repo.create(
                data={
                    "title": data.title,
                    "description": data.description,
                    "template_id": template.id if template else None,
                    "creator_id": user.id,
                    "category": data.category,
                    "sub_category": data.sub_category,
                    "scope": scope,
                    "goal_type": data.goal_type,
                    "goal_value": data.goal_value,
                    "unit": data.unit,
                    "cadence": data.cadence,
                    "goal_config": data.goal_config,
                    "verification_type": data.verification_type,
                    "difficulty": data.difficulty,
                    "visibility": data.visibility,
                    "max_participants": data.max_participants,
                    "start_date": data.start_date,
                    "end_date": data.end_date,
                    "status": ChallengeStatus.RECRUITING if scope == ChallengeScope.GROUP else ChallengeStatus.ACTIVE,
                }
            )
            await self.participant_repo.create(
                data={
                    "challenge_id": challenge.id,
                    "user_id": user.id,
                    "role": ParticipantRole.OWNER,
                    "status": ParticipantStatus.APPROVED,
                }
            )
            invite_code = None
            if scope == ChallengeScope.GROUP:
                invite = await self.invite_repo.create(
                    data={
                        "challenge_id": challenge.id,
                        "inviter_id": user.id,
                        "invitee_id": None,
                        "invite_code": _generate_invite_code(),
                        "invite_type": InviteType.CODE,
                        "expires_at": datetime.now(config.TIMEZONE) + INVITE_TTL,
                    }
                )
                invite_code = invite.invite_code
        challenge.invite_code = invite_code  # type: ignore[attr-defined]
        return challenge

    async def get_owned_or_participating(self, user: User, challenge_id: int) -> Challenge:
        challenge = await self.repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        if challenge.creator_id == user.id:
            return challenge
        participation = await self.participant_repo.get_by_user(challenge_id, user.id)
        # 승인된 참여자만 상세 접근 허용. 승인 대기(PENDING) 멤버는 차단(보안상 엄격).
        if participation is None or participation.status != ParticipantStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
        return challenge

    async def get_active_invite_code(self, challenge_id: int) -> str | None:
        """그룹 챌린지의 PENDING 상태(코드형) invite_code 를 반환. 없으면 None."""
        from app.models.challenge import ChallengeInvite, InviteStatus, InviteType  # noqa: PLC0415

        invite = (
            await ChallengeInvite.filter(
                challenge_id=challenge_id,
                invite_type=InviteType.CODE,
                status=InviteStatus.PENDING,
            )
            .order_by("-created_at")
            .first()
        )
        return invite.invite_code if invite else None

    async def get_public(self, challenge_id: int) -> Challenge:
        challenge = await self.repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        return challenge

    async def update(self, user: User, challenge_id: int, data: ChallengeUpdateRequest) -> Challenge:
        challenge = await self.repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        if challenge.creator_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="방장만 수정할 수 있습니다.")
        if data.end_date is not None and data.end_date < challenge.start_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date 가 잘못되었습니다.")
        return await self.repo.update_instance(challenge, data.model_dump(exclude_unset=True))

    async def delete(self, user: User, challenge_id: int) -> None:
        challenge = await self.repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        if challenge.creator_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="방장만 삭제할 수 있습니다.")
        await self.repo.soft_delete(challenge)

    async def list_challenges(
        self,
        *,
        user: User | None,
        scope: str | None,
        challenge_status: str | None,
        category: str | None,
        keyword: str | None,
        date_from: date | None,
        date_to: date | None,
        sort_by: str | None = None,
        page: int,
        size: int,
        mine_only: bool,
    ) -> tuple[list[Challenge], int]:
        return await self.repo.list(
            user_id=user.id if (user and mine_only) else None,
            scope=scope,
            status=challenge_status,
            category=category,
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            page=page,
            size=size,
        )


class ParticipantService:
    def __init__(self) -> None:
        self.repo = ChallengeParticipantRepository()
        self.challenge_repo = ChallengeRepository()
        self.invite_repo = ChallengeInviteRepository()

    async def list_participants(self, user: User, challenge_id: int) -> list[ChallengeParticipant]:
        challenge = await self.challenge_repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        await self._ensure_access(user, challenge)
        return await self.repo.list_for_challenge(challenge_id)

    async def join_by_code_only(self, user: User, invite_code: str) -> ChallengeParticipant:
        """invite_code 만으로 챌린지를 찾아 join 처리. (코드 입력형 참가)"""
        invite = await self.invite_repo.get_by_code(invite_code)
        if invite is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유효한 초대 코드가 아닙니다.")
        return await self.join_by_code(user, invite.challenge_id, invite_code)

    async def join_by_code(self, user: User, challenge_id: int, invite_code: str) -> ChallengeParticipant:
        invite = await self.invite_repo.get_by_code(invite_code)
        if invite is None or invite.challenge_id != challenge_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유효한 초대 코드가 아닙니다.")
        if invite.expires_at and invite.expires_at < datetime.now(config.TIMEZONE):
            await self.invite_repo.update_status(invite, InviteStatus.EXPIRED)
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="만료된 초대 코드입니다.")
        challenge = await self.challenge_repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        existing = await self.repo.get_by_user(challenge_id, user.id)
        if existing and existing.status in {ParticipantStatus.APPROVED, ParticipantStatus.PENDING}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 참여 신청한 챌린지입니다.")
        active_count = await self.repo.count_active(challenge_id)
        if active_count >= challenge.max_participants:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="모집 정원이 가득 찼습니다.")
        async with in_transaction():
            participant = await self.repo.create(
                data={
                    "challenge_id": challenge_id,
                    "user_id": user.id,
                    "role": ParticipantRole.MEMBER,
                    "status": ParticipantStatus.PENDING,
                }
            )
        return participant

    async def leave(self, user: User, challenge_id: int) -> None:
        participant = await self.repo.get_by_user(challenge_id, user.id)
        if participant is None or participant.status not in {ParticipantStatus.APPROVED, ParticipantStatus.PENDING}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참여 정보를 찾을 수 없습니다.")
        if participant.role == ParticipantRole.OWNER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="방장은 챌린지를 삭제해야 합니다.")
        await self.repo.update_status(participant, ParticipantStatus.LEFT, leaving=True)

    async def respond_to_pending(
        self,
        owner: User,
        challenge_id: int,
        target_user_id: int,
        action: str,
        reason: str | None,
    ) -> ChallengeParticipant:
        if action not in {"approve", "reject"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action 은 approve|reject 입니다.")
        challenge = await self.challenge_repo.get(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        if challenge.creator_id != owner.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="방장만 처리할 수 있습니다.")
        participant = await self.repo.get_by_user(challenge_id, target_user_id)
        if participant is None or participant.status != ParticipantStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대기 중인 참여 신청이 없습니다.")
        if action == "approve":
            active = await self.repo.count_active(challenge_id)
            if active >= challenge.max_participants:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="모집 정원이 가득 찼습니다.")
            participant = await self.repo.update_status(participant, ParticipantStatus.APPROVED)
            # 승인 후 정원 달성 시 RECRUITING → ACTIVE 자동 전환
            if active + 1 >= challenge.max_participants and challenge.status == ChallengeStatus.RECRUITING:
                await self.challenge_repo.update_instance(challenge, {"status": ChallengeStatus.ACTIVE})
            return participant
        # reject
        if reason:
            participant.left_at = datetime.now(config.TIMEZONE)
        return await self.repo.update_status(participant, ParticipantStatus.REJECTED)

    async def direct_invite(
        self,
        owner: User,
        challenge_id: int,
        request: DirectInviteRequest,
    ) -> ChallengeInvite:
        challenge = await self.challenge_repo.get(challenge_id)
        if challenge is None or challenge.creator_id != owner.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="방장만 초대할 수 있습니다.")
        existing = await self.repo.get_by_user(challenge_id, request.invitee_id)
        if existing and existing.status == ParticipantStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 참여 중인 사용자입니다.")
        return await self.invite_repo.create(
            data={
                "challenge_id": challenge_id,
                "inviter_id": owner.id,
                "invitee_id": request.invitee_id,
                "invite_type": InviteType.DIRECT,
                "expires_at": datetime.now(config.TIMEZONE) + INVITE_TTL,
            }
        )

    async def list_my_invitations(self, user: User, *, status_filter: str | None) -> list[ChallengeInvite]:
        """내가 받은(invitee) 직접 초대 목록.

        status_filter 가 비어 있으면 전부, 'PENDING' 이면 응답 대기만.
        만료된 PENDING 은 조회 시점에 EXPIRED 로 자동 전환.
        """
        from app.models.challenge import InviteStatus as _IS  # noqa: PLC0415, N814

        enum_status: _IS | None = None
        if status_filter:
            try:
                enum_status = _IS(status_filter)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="status 는 PENDING|ACCEPTED|REJECTED|EXPIRED 입니다.",
                ) from exc
        invites = await self.invite_repo.list_for_invitee(user.id, status_filter=enum_status)
        now = datetime.now(config.TIMEZONE)
        result: list[ChallengeInvite] = []
        for inv in invites:
            if inv.status == _IS.PENDING and inv.expires_at and inv.expires_at < now:
                await self.invite_repo.update_status(inv, _IS.EXPIRED)
            result.append(inv)
        if enum_status == _IS.PENDING:
            result = [i for i in result if i.status == _IS.PENDING]
        return result

    async def respond_to_direct_invite(
        self,
        user: User,
        invitation_id: int,
        action: str,
    ) -> ChallengeInvite:
        if action not in {"accept", "reject"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action 은 accept|reject 입니다.")
        invite = await self.invite_repo.get(invitation_id)
        if invite is None or invite.invitee_id != user.id or invite.status != InviteStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="처리할 초대가 없습니다.")
        if invite.expires_at and invite.expires_at < datetime.now(config.TIMEZONE):
            await self.invite_repo.update_status(invite, InviteStatus.EXPIRED)
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="만료된 초대입니다.")
        if action == "accept":
            challenge = await self.challenge_repo.get(invite.challenge_id)
            if challenge is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
            active = await self.repo.count_active(invite.challenge_id)
            if active >= challenge.max_participants:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="모집 정원이 가득 찼습니다.")
            existing = await self.repo.get_by_user(invite.challenge_id, user.id)
            if existing and existing.status == ParticipantStatus.APPROVED:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 참여 중입니다.")
            async with in_transaction():
                if existing is None:
                    await self.repo.create(
                        data={
                            "challenge_id": invite.challenge_id,
                            "user_id": user.id,
                            "role": ParticipantRole.MEMBER,
                            "status": ParticipantStatus.APPROVED,
                        }
                    )
                else:
                    await self.repo.update_status(existing, ParticipantStatus.APPROVED)
                await self.invite_repo.update_status(invite, InviteStatus.ACCEPTED)
                # 수락 후 정원 달성 시 RECRUITING → ACTIVE 자동 전환
                if active + 1 >= challenge.max_participants and challenge.status == ChallengeStatus.RECRUITING:
                    await self.challenge_repo.update_instance(challenge, {"status": ChallengeStatus.ACTIVE})
        else:
            await self.invite_repo.update_status(invite, InviteStatus.REJECTED)
        return invite

    async def _ensure_access(self, user: User, challenge: Challenge) -> None:
        if challenge.creator_id == user.id:
            return
        participant = await self.repo.get_by_user(challenge.id, user.id)
        # APPROVED 외에 PENDING(참가 신청 중) 도 챌린지 상세/멤버 목록 조회 허용
        # — 본인의 신청 상태를 확인할 수 있어야 한다
        if participant is None or participant.status not in {
            ParticipantStatus.APPROVED,
            ParticipantStatus.PENDING,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")


class VerificationService:
    def __init__(self) -> None:
        self.repo = ChallengeVerificationRepository()
        self.participant_repo = ChallengeParticipantRepository()
        self.challenge_repo = ChallengeRepository()
        self.image_job_repo = ImageVerificationJobRepository()
        self.attachment_repo = ChallengeVerificationAttachmentRepository()
        self.reaction_repo = ChallengeReactionRepository()
        self.image_verifier = ImageVerifier()
        self.reward_service = RewardService()
        self.pet_service = PetService()
        self.rescue_service = RescueTicketService()

    async def create(self, user: User, data: VerificationCreateRequest) -> ChallengeVerification:  # noqa: C901
        challenge = await self.challenge_repo.get(data.challenge_id)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        if data.verified_date < challenge.start_date or data.verified_date > challenge.end_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="챌린지 기간 외 인증입니다.")
        participant = await self.participant_repo.get_by_user(challenge.id, user.id)
        if participant is None or participant.status != ParticipantStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="참여 중인 챌린지가 아닙니다.")
        # 명상 챌린지는 타이머(CHECK) 인증으로 처리 — verification_type 무관하게 허용
        is_meditation = challenge.category == ChallengeCategory.MEDITATION
        if not is_meditation and not _method_matches(challenge.verification_type, data.method):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이 챌린지는 {challenge.verification_type.value} 인증만 허용합니다.",
            )

        # 동일 일자/메서드 중복 인증 방지. unique_together(participant, verified_date, method)
        # 가 DB 레벨에 걸려있어 그대로 두면 IntegrityError → 500 으로 떨어지고 클라이언트는
        # "네트워크 오류" 를 보게 된다. 명시적으로 409 + 한국어 사유로 반환한다.
        existing = await ChallengeVerification.filter(
            participant_id=participant.id,
            verified_date=data.verified_date,
            method=data.method,
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="오늘은 이미 해당 챌린지의 인증을 완료했습니다.",
            )

        if data.method == VerificationMethod.CHECK:
            # 체크 인증: checked=True → 달성(APPROVED), checked=False → 미달성(REJECTED)
            initial_status = VerificationStatus.APPROVED if data.checked is True else VerificationStatus.REJECTED
        elif data.method == VerificationMethod.SHIELD:
            initial_status = VerificationStatus.APPROVED
        else:
            # PHOTO → AI 검증 대기
            initial_status = VerificationStatus.PENDING

        async with in_transaction():
            verification = await self.repo.create(
                data={
                    "challenge_id": challenge.id,
                    "participant_id": participant.id,
                    "user_id": user.id,
                    "method": data.method,
                    "verified_date": data.verified_date,
                    "checked": data.checked,
                    "answers": data.answers or {},
                    "photo_file_id": data.photo_file_id,
                    "shield_inventory_id": data.shield_inventory_id,
                    "caption": data.caption,
                    "verified_duration_seconds": data.duration_seconds,
                    "status": initial_status,
                }
            )
            if data.method == VerificationMethod.PHOTO and data.photo_file_id is not None:
                await self.attachment_repo.create_many(verification.id, [data.photo_file_id])
                job = await self.image_job_repo.create(
                    data={
                        "verification_id": verification.id,
                        "status": VerificationJobStatus.QUEUED,
                        "result": {},
                        "model_version": self.image_verifier.model_version,
                    }
                )
                # ai_worker 가 처리하도록 Redis 큐에 push.
                # 카테고리/세부카테고리 정보가 SigLIP2 zero-shot 프롬프트에 필요.
                # Redis 가 없는 로컬 환경에서는 enqueue 실패 → verification 자체는 PENDING 으로 응답하고
                # AI 검증은 best-effort 로 skip. (운영 환경에서는 Redis 필수)
                from app.core.queue import enqueue_image_verification  # noqa: PLC0415

                try:
                    await enqueue_image_verification(
                        {
                            "job_id": job.id,
                            "verification_id": verification.id,
                            "file_id": data.photo_file_id,
                            "category": challenge.category.value,
                            "sub_category": challenge.sub_category.value if challenge.sub_category else None,
                            # goal_config 도 함께 전달해 SigLIP2 프롬프트 동적 생성에 사용
                            "goal_config": challenge.goal_config or {},
                        }
                    )
                except Exception:  # pragma: no cover — 로컬 Redis 부재 시 폴백
                    import logging  # noqa: PLC0415

                    logging.getLogger(__name__).warning(
                        "enqueue_image_verification failed (redis unavailable). verification=%s",
                        verification.id,
                    )
            if data.method == VerificationMethod.SHIELD:
                await self.rescue_service.consume(user.id, challenge.id, data.verified_date)
            if initial_status == VerificationStatus.APPROVED:
                await self.participant_repo.add_score(participant, points=1)
                await self.reward_service.grant_daily(
                    user_id=user.id,
                    challenge_id=challenge.id,
                    verification_id=verification.id,
                )
                # 펫이 있는 경우 인증당 XP 가산. 펫 없으면 무시.
                await self.pet_service.grant_xp(
                    user.id,
                    XP_FROM_CHALLENGE_VERIFICATION,
                    source=GrowthEventSource.CHALLENGE,
                    source_id=verification.id,
                )

        # 주간 활동량 EXP 적립 (방지권 제외). best-effort.
        if data.method != VerificationMethod.SHIELD:
            try:
                from app.models.experience import XpKind
                from app.services.experience import ExperienceService

                await ExperienceService().award(user_id=user.id, kind=XpKind.CHALLENGE_VERIFY)
            except Exception:
                pass

        return verification

    async def list_records(
        self,
        user: User,
        *,
        challenge_id: int | None,
        target_user_id: int | None,
        verified_date: date | None,
        date_from: date | None,
        date_to: date | None,
        verification_status: str | None,
        method: str | None,
        page: int,
        size: int,
    ) -> tuple[list[ChallengeVerification], int]:
        # 본인 또는 동일 챌린지 참여자 데이터만 조회 가능
        effective_user_id = target_user_id if target_user_id is not None else user.id
        if effective_user_id != user.id:
            if challenge_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="다른 사용자 인증 조회는 challenge_id 가 필요합니다.",
                )
            participant = await self.participant_repo.get_by_user(challenge_id, user.id)
            if participant is None or participant.status != ParticipantStatus.APPROVED:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
        return await self.repo.list(
            challenge_id=challenge_id,
            user_id=effective_user_id,
            verified_date=verified_date,
            date_from=date_from,
            date_to=date_to,
            status=verification_status,
            method=method,
            page=page,
            size=size,
        )

    async def get_owned(self, user: User, verification_id: int) -> ChallengeVerification:
        verification = await self.repo.get(verification_id)
        if verification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인증 기록을 찾을 수 없습니다.")
        if verification.user_id != user.id:
            participant = await self.participant_repo.get_by_user(verification.challenge_id, user.id)
            if participant is None or participant.status != ParticipantStatus.APPROVED:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
        return verification

    async def update(
        self,
        user: User,
        verification_id: int,
        data: VerificationUpdateRequest,
    ) -> ChallengeVerification:
        verification = await self.get_owned(user, verification_id)
        if verification.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인만 수정할 수 있습니다.")
        if data.status is None:
            return verification
        return await self.repo.update_status(verification, data.status, reason=data.rejection_reason)

    async def delete(self, user: User, verification_id: int) -> None:
        verification = await self.get_owned(user, verification_id)
        if verification.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인만 삭제할 수 있습니다.")
        await self.repo.soft_delete(verification)

    async def get_feed(
        self,
        user: User,
        challenge_id: int,
        page: int,
        size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        participant = await self.participant_repo.get_by_user(challenge_id, user.id)
        if participant is None or participant.status != ParticipantStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
        items, total = await self.repo.list_feed(challenge_id, page, size)
        verification_ids = [v.id for v in items]
        liked_ids = await self.reaction_repo.get_liked_verification_ids(user.id, verification_ids)
        result: list[dict[str, Any]] = []
        for v in items:
            u = getattr(v, "user", None)
            result.append(
                {
                    "id": v.id,
                    "user_id": v.user_id,
                    "user_nickname": (u.nickname or u.name) if u else None,
                    "method": v.method,
                    "verified_date": v.verified_date,
                    "caption": getattr(v, "caption", None),
                    "photo_file_id": v.photo_file_id,
                    "verified_duration_seconds": getattr(v, "verified_duration_seconds", None),
                    "like_count": v.like_count,
                    "comment_count": v.comment_count,
                    "my_like": v.id in liked_ids,
                    "created_at": v.created_at,
                }
            )
        return result, total


class ReactionService:
    def __init__(self) -> None:
        self.repo = ChallengeReactionRepository()
        self.verification_repo = ChallengeVerificationRepository()
        self.participant_repo = ChallengeParticipantRepository()

    async def list(self, user: User, verification_id: int) -> tuple[ChallengeVerification, list[ChallengeReaction], bool]:
        verification = await self._access(user, verification_id)
        comments = await self.repo.list_comments_with_replies(verification_id)
        my_like = await self.repo.get_user_like(verification_id, user.id) is not None
        return verification, comments, my_like

    async def toggle_like(
        self,
        user: User,
        verification_id: int,
    ) -> tuple[bool, int]:
        """좋아요 토글. (liked: bool, new_like_count: int) 반환."""
        verification = await self._access(user, verification_id)
        existing = await self.repo.get_user_like(verification_id, user.id)
        if existing:
            async with in_transaction():
                await self.repo.soft_delete(existing)
                await self.verification_repo.increment_counter(verification, likes=-1)
            return False, max(0, verification.like_count - 1)
        async with in_transaction():
            await self.repo.create(
                data={
                    "verification_id": verification_id,
                    "user_id": user.id,
                    "type": ReactionType.LIKE,
                    "content": None,
                }
            )
            await self.verification_repo.increment_counter(verification, likes=1)
        return True, verification.like_count + 1

    async def create(
        self,
        user: User,
        verification_id: int,
        data: ReactionCreateRequest,
    ) -> ChallengeReaction:
        verification = await self._access(user, verification_id)
        async with in_transaction():
            reaction = await self.repo.create(
                data={
                    "verification_id": verification_id,
                    "user_id": user.id,
                    "type": data.type,
                    "content": data.content,
                }
            )
            if data.type == ReactionType.LIKE:
                await self.verification_repo.increment_counter(verification, likes=1)
            else:
                await self.verification_repo.increment_counter(verification, comments=1)
        return reaction

    async def create_reply(
        self,
        user: User,
        verification_id: int,
        parent_reaction_id: int,
        content: str,
    ) -> ChallengeReaction:
        await self._access(user, verification_id)
        parent = await self.repo.get(parent_reaction_id)
        if parent is None or parent.type != ReactionType.COMMENT:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")
        async with in_transaction():
            reply = await self.repo.create(
                data={
                    "verification_id": verification_id,
                    "user_id": user.id,
                    "type": ReactionType.COMMENT,
                    "content": content,
                    "parent_id": parent_reaction_id,
                }
            )
            await self.verification_repo.increment_counter(
                await self.verification_repo.get(verification_id),
                comments=1,
            )
        return reply

    async def update(self, user: User, reaction_id: int, data: ReactionUpdateRequest) -> ChallengeReaction:
        reaction = await self.repo.get(reaction_id)
        if reaction is None or reaction.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")
        if reaction.type != ReactionType.COMMENT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="댓글만 수정할 수 있습니다.")
        return await self.repo.update_content(reaction, data.content)

    async def delete(self, user: User, reaction_id: int) -> None:
        reaction = await self.repo.get(reaction_id)
        if reaction is None or reaction.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="반응을 찾을 수 없습니다.")
        verification = await self.verification_repo.get(reaction.verification_id)
        async with in_transaction():
            await self.repo.soft_delete(reaction)
            if verification:
                if reaction.type == ReactionType.LIKE:
                    await self.verification_repo.increment_counter(verification, likes=-1)
                else:
                    await self.verification_repo.increment_counter(verification, comments=-1)

    async def _access(self, user: User, verification_id: int) -> ChallengeVerification:
        verification = await self.verification_repo.get(verification_id)
        if verification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인증을 찾을 수 없습니다.")
        if verification.user_id == user.id:
            return verification
        participant = await self.participant_repo.get_by_user(verification.challenge_id, user.id)
        if participant is None or participant.status != ParticipantStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
        return verification


class ChallengeSummaryService:
    def __init__(self) -> None:
        self.repo = ChallengeVerificationRepository()
        self.reward_service = RewardService()

    async def summarize(
        self,
        user: User,
        period: str,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        if period not in {"weekly", "monthly"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period 는 weekly|monthly 입니다.")
        today = datetime.now(config.TIMEZONE).date()
        if date_from is None and date_to is None:
            if period == "weekly":
                date_from = today - timedelta(days=today.weekday())
            else:
                date_from = today.replace(day=1)
            date_to = today
        summary = await self.repo.aggregate_summary(user.id, date_from, date_to)
        rewards_estimated = summary["success_count"] * self.reward_service.DAILY_OPTIONS[0]
        return {
            "period": period,
            "from_date": date_from,
            "to_date": date_to,
            "total": summary["total"],
            "success_count": summary["success_count"],
            "fail_count": summary["fail_count"],
            "pending_count": summary["pending_count"],
            "rewards_estimated": rewards_estimated,
            "per_challenge": summary["per_challenge"],
        }


class ChallengeRecommendationService:
    def __init__(self) -> None:
        self.repo = ChallengeRecommendationRepository()
        self.template_repo = ChallengeTemplateRepository()
        self.participant_repo = ChallengeParticipantRepository()
        self.recommender = ChallengeRecommender()

    async def for_prediction(
        self,
        user: User,
        prediction_id: int,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        risk = await DiseaseRisk.get_or_none(id=prediction_id, user_id=user.id)
        if risk is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
        hints = self.recommender.hints_for(risk.disease_type, risk.risk_level, limit)
        templates = await self.template_repo.list_active()
        results: list[dict[str, Any]] = []
        for hint in hints:
            template = next(
                (
                    t
                    for t in templates
                    if t.category == hint.category
                    and (hint.sub_category is None or t.sub_category == hint.sub_category)
                ),
                None,
            )
            already_joined = False
            if template is not None:
                already_joined = await _is_user_joined_for_template(user.id, template.id)
                await self.repo.upsert(
                    user_id=user.id,
                    disease_risk_id=risk.id,
                    template_id=template.id,
                    challenge_id=None,
                    priority=hint.priority.value,
                    reason=hint.reason,
                )
            results.append(
                {
                    "template_id": template.id if template else None,
                    "challenge_id": None,
                    "category": hint.category,
                    "sub_category": hint.sub_category,
                    "title": template.title if template else hint.category.value,
                    "priority": hint.priority,
                    "reason": hint.reason,
                    "already_joined": already_joined,
                }
            )
        return results


async def _is_user_joined_for_template(user_id: int, template_id: int) -> bool:
    return await ChallengeParticipant.filter(
        user_id=user_id,
        status=ParticipantStatus.APPROVED,
        challenge__template_id=template_id,
    ).exists()


def _method_matches(challenge_verification_type: VerificationType, method: VerificationMethod) -> bool:
    if method == VerificationMethod.SHIELD:
        return True
    if challenge_verification_type == VerificationType.CHECK:
        return method == VerificationMethod.CHECK
    return method == VerificationMethod.PHOTO


def _generate_invite_code(length: int = 8) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def total_pages(total: int, size: int) -> int:
    if size <= 0:
        return 0
    return math.ceil(total / size)


# 부수효과 처리용 헬퍼: 인증 누락 누적 → 자동 강퇴. 챌린지 종료/스케줄러에서 호출.
async def evaluate_missed_kick(participant_id: int) -> None:
    participant = await ChallengeParticipant.get_or_none(id=participant_id)
    if participant is None:
        return
    if participant.missed_count >= MAX_MISSED_BEFORE_KICK:
        participant.status = ParticipantStatus.KICKED
        participant.left_at = datetime.now(config.TIMEZONE)
        await participant.save(update_fields=["status", "left_at"])
