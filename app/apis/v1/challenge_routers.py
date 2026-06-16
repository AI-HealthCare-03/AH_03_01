from collections import defaultdict
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.challenge import (
    ChallengeCategoryResponse,
    ChallengeCreateRequest,
    ChallengeListItem,
    ChallengeListResponse,
    ChallengeRecommendationItem,
    ChallengeRecommendationResponse,
    ChallengeResponse,
    ChallengeSummaryResponse,
    ChallengeTemplateResponse,
    ChallengeUpdateRequest,
    DirectInviteRequest,
    InvitationActionResponse,
    InviteCreateResponse,
    ParticipantResponse,
    ReactionCreateRequest,
    ReactionListResponse,
    ReactionResponse,
    ReactionUpdateRequest,
    ReactionWithReplies,
    VerificationCreateRequest,
    VerificationFeedItem,
    VerificationFeedResponse,
    VerificationListResponse,
    VerificationResponse,
    VerificationUpdateRequest,
)
from app.models.challenge import (
    ChallengeCategory,
    ChallengeParticipant,
    ChallengeReaction,
    ChallengeScope,
    ChallengeStatus,
    ChallengeVerification,
    ChallengeVisibility,
    ParticipantStatus,
    ReactionType,
    VerificationMethod,
    VerificationStatus,
)
from app.models.notifications import NotificationType
from app.models.users import User
from app.repositories.notification_repository import NotificationRepository
from app.services.challenge import (
    ChallengeRecommendationService,
    ChallengeService,
    ChallengeSummaryService,
    ChallengeTemplateService,
    ParticipantService,
    ReactionService,
    VerificationService,
    total_pages,
)


def _effective_status(ch_status: ChallengeStatus, end_date: date) -> ChallengeStatus:
    """크론잡 실행 전이라도 end_date가 지난 챌린지는 COMPLETED로 반환한다."""
    if ch_status in (ChallengeStatus.ACTIVE, ChallengeStatus.RECRUITING) and end_date < date.today():
        return ChallengeStatus.COMPLETED
    return ch_status


challenge_categories_router = APIRouter(prefix="/challenge-categories", tags=["challenge-categories"])
challenges_router = APIRouter(prefix="/challenges", tags=["challenges"])
challenge_invitations_router = APIRouter(prefix="/challenge-invitations", tags=["challenge-invitations"])
challenge_verifications_router = APIRouter(prefix="/challenge-verifications", tags=["challenge-verifications"])
challenge_summaries_router = APIRouter(prefix="/challenge-summaries", tags=["challenge-summaries"])
challenge_recommendations_router = APIRouter(prefix="/challenge-recommendations", tags=["challenge-recommendations"])


# ---------------------------------------------------------------------------
# Categories / Templates
# ---------------------------------------------------------------------------


@challenge_categories_router.get("", status_code=status.HTTP_200_OK)
async def list_challenge_categories(
    _: Annotated[User, Depends(get_request_user)],
    template_service: Annotated[ChallengeTemplateService, Depends(ChallengeTemplateService)],
    category: Annotated[ChallengeCategory | None, Query()] = None,
) -> Response:
    templates = await template_service.list_active(category.value if category else None)
    grouped: dict[ChallengeCategory, list[ChallengeTemplateResponse]] = defaultdict(list)
    sub_map: dict[ChallengeCategory, set[Any]] = defaultdict(set)
    for tpl in templates:
        grouped[tpl.category].append(ChallengeTemplateResponse.model_validate(tpl))
        if tpl.sub_category:
            sub_map[tpl.category].add(tpl.sub_category)
    payload = [
        ChallengeCategoryResponse(
            category=cat,
            sub_categories=sorted(sub_map[cat], key=lambda s: s.value),
            templates=items,
        ).model_dump()
        for cat, items in grouped.items()
    ]
    return Response({"categories": payload}, status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Challenges CRUD
# ---------------------------------------------------------------------------


@challenges_router.post("", status_code=status.HTTP_201_CREATED)
async def create_challenge(
    body: ChallengeCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeService, Depends(ChallengeService)],
    scope: Annotated[ChallengeScope | None, Query()] = None,  # 명시적 스코프 강제 (선택)
) -> Response:
    if scope is not None:
        if scope == ChallengeScope.PERSONAL and body.max_participants != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="개인 챌린지는 max_participants 가 1 이어야 합니다.",
            )
        if scope == ChallengeScope.GROUP and body.max_participants <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="그룹 챌린지는 max_participants 가 2 이상이어야 합니다.",
            )
    challenge = await service.create(user, body)
    payload = ChallengeResponse.model_validate(challenge).model_dump()
    if hasattr(challenge, "invite_code"):
        payload["invite_code"] = challenge.invite_code  # type: ignore[attr-defined]
    return Response(payload, status_code=status.HTTP_201_CREATED)


@challenges_router.get("", response_model=ChallengeListResponse, status_code=status.HTTP_200_OK)
async def list_challenges(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeService, Depends(ChallengeService)],
    scope: Annotated[ChallengeScope | None, Query()] = None,
    challenge_status: Annotated[ChallengeStatus | None, Query(alias="status")] = None,
    category: Annotated[ChallengeCategory | None, Query()] = None,
    visibility: Annotated[ChallengeVisibility | None, Query()] = None,
    keyword: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    mine: Annotated[bool, Query()] = False,
    left_only: Annotated[bool, Query(alias="leftOnly")] = False,
    sort_by: Annotated[str | None, Query(alias="sortBy")] = None,  # created_at | end_date
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Response:
    items, total = await service.list_challenges(
        user=user,
        scope=scope.value if scope else None,
        challenge_status=challenge_status.value if challenge_status else None,
        category=category.value if category else None,
        visibility=visibility.value if visibility else None,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        page=page,
        size=size,
        mine_only=mine,
        left_only=left_only,
    )

    # 사용자별 달성 현황 일괄 조회
    challenge_ids = [ch.id for ch in items]
    approved_counts: dict[int, int] = {}
    missed_counts: dict[int, int] = {}
    participant_statuses: dict[int, str] = {}
    group_all_approved: dict[int, int] = {}
    group_active_members: dict[int, int] = {}
    if challenge_ids:
        verif_rows = await ChallengeVerification.filter(
            challenge_id__in=challenge_ids,
            user_id=user.id,
            status=VerificationStatus.APPROVED,
        ).values("challenge_id")
        for row in verif_rows:
            cid = row["challenge_id"]
            approved_counts[cid] = approved_counts.get(cid, 0) + 1

        part_rows = await ChallengeParticipant.filter(
            challenge_id__in=challenge_ids,
            user_id=user.id,
        ).values("challenge_id", "missed_count", "status")
        for row in part_rows:
            missed_counts[row["challenge_id"]] = row["missed_count"] or 0
            participant_statuses[row["challenge_id"]] = row["status"]

        # 그룹 챌린지 전체 달성률 계산용 배치 조회
        group_ids = [ch.id for ch in items if ch.scope == ChallengeScope.GROUP]
        if group_ids:
            all_verif_rows = await ChallengeVerification.filter(
                challenge_id__in=group_ids,
                status=VerificationStatus.APPROVED,
            ).values("challenge_id")
            for row in all_verif_rows:
                cid = row["challenge_id"]
                group_all_approved[cid] = group_all_approved.get(cid, 0) + 1

            active_member_rows = await ChallengeParticipant.filter(
                challenge_id__in=group_ids,
                status=ParticipantStatus.APPROVED,
            ).values("challenge_id")
            for row in active_member_rows:
                cid = row["challenge_id"]
                group_active_members[cid] = group_active_members.get(cid, 0) + 1

    def _total_days(ch) -> int:
        return max(1, (ch.end_date - ch.start_date).days + 1)

    def _achievement_rate(ch) -> int:
        td = _total_days(ch)
        if ch.scope == ChallengeScope.GROUP:
            all_approved = group_all_approved.get(ch.id, 0)
            active_members = max(1, group_active_members.get(ch.id, 0))
            return round(all_approved / (td * active_members) * 100)
        else:
            return round(approved_counts.get(ch.id, 0) / td * 100)

    payload = ChallengeListResponse(
        page=page,
        size=size,
        total_elements=total,
        total_pages=total_pages(total, size),
        items=[
            ChallengeListItem(
                id=ch.id,
                title=ch.title,
                scope=ch.scope,
                status=_effective_status(ch.status, ch.end_date),
                category=ch.category,
                visibility=ch.visibility,
                max_participants=ch.max_participants,
                start_date=ch.start_date,
                end_date=ch.end_date,
                created_at=ch.created_at,
                my_progress=approved_counts.get(ch.id, 0),
                total_days=_total_days(ch),
                my_progress_percent=round(approved_counts.get(ch.id, 0) / _total_days(ch) * 100, 1),
                achievement_rate=_achievement_rate(ch),
                missed_count=missed_counts.get(ch.id, 0),
                my_participant_status=participant_statuses.get(ch.id),
                participant_count=group_active_members.get(ch.id, 0) if ch.scope == ChallengeScope.GROUP else None,
            )
            for ch in items
        ],
    )

    # 참여하기 탭: 정원이 찬 그룹 챌린지 제외 (공개/비공개 무관)
    if not mine:
        payload.items = [
            item for item in payload.items
            if not (
                item.max_participants is not None
                and group_active_members.get(item.id, 0) >= item.max_participants
            )
        ]
        payload.total_elements = len(payload.items)

    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@challenges_router.get("/{challenge_id}", response_model=ChallengeResponse, status_code=status.HTTP_200_OK)
async def get_challenge(
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeService, Depends(ChallengeService)],
) -> Response:
    challenge = await service.get_public(challenge_id)
    is_creator = challenge.creator_id == user.id
    participation = await ChallengeParticipant.filter(
        challenge_id=challenge_id, user_id=user.id,
    ).first()
    is_member = is_creator or (
        participation is not None and participation.status == ParticipantStatus.APPROVED
    )
    my_progress = await ChallengeVerification.filter(
        challenge_id=challenge_id,
        user_id=user.id,
        status=VerificationStatus.APPROVED,
    ).count()
    total_days = max(1, (challenge.end_date - challenge.start_date).days + 1)

    participant_count = None
    if challenge.scope == ChallengeScope.GROUP:
        # 그룹 달성률: 전체 멤버 인증 합계 / (기간 × 활성 멤버 수) × 100
        all_approved = await ChallengeVerification.filter(
            challenge_id=challenge_id,
            status=VerificationStatus.APPROVED,
        ).count()
        active_members = await ChallengeParticipant.filter(
            challenge_id=challenge_id,
            status=ParticipantStatus.APPROVED,
        ).count()
        participant_count = active_members
        denominator = total_days * max(1, active_members)
        achievement_rate = round(all_approved / denominator * 100)
    else:
        # 개인 달성률: 내 인증 수 / 기간 × 100
        achievement_rate = round(my_progress / total_days * 100)

    payload = ChallengeResponse.model_validate(challenge).model_dump()
    payload["is_member"] = is_member
    payload["status"] = _effective_status(challenge.status, challenge.end_date).value
    payload["my_progress"] = my_progress
    payload["total_days"] = total_days
    payload["achievement_rate"] = achievement_rate
    payload["participant_count"] = participant_count
    # 그룹 챌린지의 경우 참여자/방장에게 invite_code 노출 (코드 복사 기능)
    if challenge.scope.value == "GROUP" and is_member:
        invite_code = await service.get_active_invite_code(challenge.id)
        if invite_code:
            payload["invite_code"] = invite_code
    return Response(payload, status_code=status.HTTP_200_OK)


@challenges_router.get(
    "/{challenge_id}/feed",
    status_code=status.HTTP_200_OK,
)
async def get_challenge_feed(
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[VerificationService, Depends(VerificationService)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Response:
    items, total = await service.get_feed(user, challenge_id, page, size)
    payload = VerificationFeedResponse(
        page=page,
        size=size,
        total_elements=total,
        total_pages=total_pages(total, size),
        items=[VerificationFeedItem(**item) for item in items],
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@challenges_router.patch("/{challenge_id}", response_model=ChallengeResponse, status_code=status.HTTP_200_OK)
async def update_challenge(
    challenge_id: int,
    body: ChallengeUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeService, Depends(ChallengeService)],
) -> Response:
    challenge = await service.update(user, challenge_id, body)
    return Response(ChallengeResponse.model_validate(challenge).model_dump(), status_code=status.HTTP_200_OK)


@challenges_router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeService, Depends(ChallengeService)],
) -> Response:
    await service.delete(user, challenge_id)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Participants / Invitations
# ---------------------------------------------------------------------------


@challenges_router.get(
    "/{challenge_id}/participants",
    status_code=status.HTTP_200_OK,
)
async def list_participants(
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
) -> Response:
    from app.models.challenge import Challenge  # noqa: PLC0415

    participants = await service.list_participants(user, challenge_id)

    # 챌린지 기간 조회 (달성률 % 계산용)
    challenge_obj = await Challenge.get(id=challenge_id)
    total_days = max(1, (challenge_obj.end_date - challenge_obj.start_date).days + 1)

    # 멤버별 APPROVED 인증 수 일괄 조회
    participant_user_ids = [p.user_id for p in participants]
    progress_map: dict[str, int] = {}
    if participant_user_ids:
        verif_rows = await ChallengeVerification.filter(
            challenge_id=challenge_id,
            user_id__in=participant_user_ids,
            status=VerificationStatus.APPROVED,
        ).values("user_id")
        for row in verif_rows:
            uid = str(row["user_id"])
            progress_map[uid] = progress_map.get(uid, 0) + 1

    # ParticipantResponse 에는 user 필드가 없으므로, 직렬화한 dict 에 user 메타를 inline 추가
    payload: list[dict[str, Any]] = []
    for p in participants:
        item = ParticipantResponse.model_validate(p).model_dump(mode="json")
        u = getattr(p, "user", None)
        item["user"] = (
            {
                "id": str(u.id),
                "name": u.name,
                "nickname": u.nickname,
            }
            if u is not None
            else None
        )
        progress_days = progress_map.get(str(p.user_id), 0)
        item["progress_days"] = progress_days
        item["achievement_rate"] = round(progress_days / total_days * 100)
        payload.append(item)
    # 프론트(ParticipantListResponse)는 items 키를 기대한다. participants 별칭은 호환용.
    return Response(
        {"items": payload, "participants": payload, "total": len(payload)},
        status_code=status.HTTP_200_OK,
    )


@challenges_router.post(
    "/join-by-code",
    status_code=status.HTTP_201_CREATED,
)
async def join_challenge_by_code(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
    invite_code_q: Annotated[str | None, Query(alias="inviteCode")] = None,
    request: Request = None,  # type: ignore[assignment]
) -> Response:
    """invite_code 만으로 챌린지를 찾아 참가. 코드형 입력 화면(/challenges/join)에서 사용."""
    code = invite_code_q
    if code is None and request is not None:
        try:
            body = await request.json()
        except ValueError:
            body = {}
        if isinstance(body, dict):
            code = body.get("invite_code")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invite_code 가 필요합니다.")
    participant = await service.join_by_code_only(user, code)
    return Response(
        ParticipantResponse.model_validate(participant).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@challenges_router.post(
    "/{challenge_id}/participants",
    status_code=status.HTTP_201_CREATED,
)
async def participant_action(
    request: Request,
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
    action: Annotated[str, Query(description="invite|join")] = "join",
    invite_code_q: Annotated[str | None, Query(alias="inviteCode")] = None,
) -> Response:
    # action 에 따라 두 종류의 body 를 받기 위해 수동 파싱.
    try:
        body = await request.json()
    except ValueError:
        body = {}
    if body is None:
        body = {}
    if action == "join":
        code = invite_code_q or (body.get("invite_code") if isinstance(body, dict) else None)
        if code:
            participant = await service.join_by_code(user, challenge_id, code)
        else:
            participant = await service.join_public(user, challenge_id)
        return Response(
            ParticipantResponse.model_validate(participant).model_dump(mode="json"),
            status_code=status.HTTP_201_CREATED,
        )
    if action == "invite":
        if not isinstance(body, dict) or "invitee_id" not in body:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invitee_id 가 필요합니다.")
        try:
            direct_invite_body = DirectInviteRequest.model_validate(body)
        except ValidationError as exc:
            raise RequestValidationError(errors=exc.errors()) from exc
        invite = await service.direct_invite(user, challenge_id, direct_invite_body)
        return Response(
            InviteCreateResponse(
                invite_id=invite.id,
                invite_code=invite.invite_code or "",
                expires_at=invite.expires_at,
            ).model_dump(mode="json"),
            status_code=status.HTTP_201_CREATED,
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action 은 join|invite 입니다.")


@challenges_router.delete(
    "/{challenge_id}/participants",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def leave_challenge(
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
) -> Response:
    await service.leave(user, challenge_id)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)


@challenges_router.delete(
    "/{challenge_id}/participants/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def kick_participant(
    challenge_id: int,
    target_user_id: UUID,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
) -> Response:
    await service.kick_participant(user, challenge_id, target_user_id)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)


@challenges_router.patch(
    "/{challenge_id}/participants/{target_user_id}",
    status_code=status.HTTP_200_OK,
)
async def respond_to_pending(
    challenge_id: int,
    target_user_id: UUID,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
    action: Annotated[str, Query(description="approve|reject")],
    reason: Annotated[str | None, Query()] = None,
) -> Response:
    participant = await service.respond_to_pending(user, challenge_id, target_user_id, action, reason)
    return Response(
        {
            "user_id": str(participant.user_id),
            "status": participant.status.value,
            "updated_at": participant.joined_at.isoformat(),
        },
        status_code=status.HTTP_200_OK,
    )


@challenge_invitations_router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def list_my_invitations(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
    status_q: Annotated[str | None, Query(alias="status")] = None,
) -> Response:
    """내가 받은 직접 초대(invitee=me) 목록. status=PENDING 으로 응답 대기만 필터링 가능."""
    invites = await service.list_my_invitations(user, status_filter=status_q)
    # 챌린지 메타 같이 채워 한 번에 화면에 그릴 수 있게.
    items: list[dict[str, Any]] = []
    for inv in invites:
        await inv.fetch_related("challenge", "inviter")
        items.append(
            {
                "id": inv.id,
                "challenge_id": inv.challenge_id,
                "challenge_title": inv.challenge.title if inv.challenge else None,
                "challenge_category": inv.challenge.category.value
                if inv.challenge and inv.challenge.category
                else None,
                "inviter_id": str(inv.inviter_id) if inv.inviter_id else None,  # type: ignore[attr-defined]
                "inviter_name": (inv.inviter.nickname or inv.inviter.name) if inv.inviter else None,
                "status": inv.status.value,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "created_at": inv.created_at.isoformat(),
            }
        )
    return Response({"items": items}, status_code=status.HTTP_200_OK)


@challenge_invitations_router.patch(
    "/{invitation_id}",
    response_model=InvitationActionResponse,
    status_code=status.HTTP_200_OK,
)
async def respond_to_invitation(
    invitation_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ParticipantService, Depends(ParticipantService)],
    action: Annotated[str, Query(description="accept|reject")],
) -> Response:
    invite = await service.respond_to_direct_invite(user, invitation_id, action)
    payload = InvitationActionResponse(id=invite.id, status=invite.status, responded_at=invite.responded_at)
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Verifications
# ---------------------------------------------------------------------------


@challenge_verifications_router.post("", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
async def create_verification(
    body: VerificationCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[VerificationService, Depends(VerificationService)],
    method: Annotated[VerificationMethod | None, Query()] = None,
) -> Response:
    if method is not None and method != body.method:
        body.method = method
    verification, earned_points = await service.create(user, body)
    payload = VerificationResponse.model_validate(verification).model_dump()
    payload["earned_points"] = earned_points
    return Response(payload, status_code=status.HTTP_201_CREATED)


@challenge_verifications_router.get("", response_model=VerificationListResponse, status_code=status.HTTP_200_OK)
async def list_verifications(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[VerificationService, Depends(VerificationService)],
    challenge_id: Annotated[int | None, Query(alias="challengeId")] = None,
    target_user_id: Annotated[int | None, Query(alias="userId")] = None,
    verified_date: Annotated[date | None, Query(alias="date")] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    verification_status: Annotated[VerificationStatus | None, Query(alias="status")] = None,
    method: Annotated[VerificationMethod | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Response:
    items, total = await service.list_records(
        user=user,
        challenge_id=challenge_id,
        target_user_id=target_user_id,
        verified_date=verified_date,
        date_from=date_from,
        date_to=date_to,
        verification_status=verification_status.value if verification_status else None,
        method=method.value if method else None,
        page=page,
        size=size,
    )
    payload = VerificationListResponse(
        page=page,
        size=size,
        total_elements=total,
        total_pages=total_pages(total, size),
        items=[VerificationResponse.model_validate(v) for v in items],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@challenge_verifications_router.get(
    "/{verification_id}",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_verification(
    verification_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[VerificationService, Depends(VerificationService)],
) -> Response:
    verification = await service.get_owned(user, verification_id)
    return Response(
        VerificationResponse.model_validate(verification).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@challenge_verifications_router.patch(
    "/{verification_id}",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_verification(
    verification_id: int,
    body: VerificationUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[VerificationService, Depends(VerificationService)],
) -> Response:
    verification = await service.update(user, verification_id, body)
    return Response(
        VerificationResponse.model_validate(verification).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@challenge_verifications_router.delete(
    "/{verification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_verification(
    verification_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[VerificationService, Depends(VerificationService)],
) -> Response:
    await service.delete(user, verification_id)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------


@challenge_verifications_router.get(
    "/{verification_id}/reactions",
    response_model=ReactionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_reactions(
    verification_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ReactionService, Depends(ReactionService)],
) -> Response:
    verification, comments, my_like = await service.list(user, verification_id)
    payload = ReactionListResponse(
        like_count=verification.like_count,
        my_like=my_like,
        comments=[
            ReactionWithReplies(
                **ReactionResponse.model_validate(c).model_dump(),
                replies=[ReactionResponse.model_validate(r) for r in getattr(c, "reply_list", [])],
            )
            for c in comments
        ],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@challenge_verifications_router.post(
    "/{verification_id}/reactions/toggle-like",
    status_code=status.HTTP_200_OK,
)
async def toggle_like(
    verification_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ReactionService, Depends(ReactionService)],
) -> Response:
    liked, like_count = await service.toggle_like(user, verification_id)
    if liked:
        verification = await ChallengeVerification.get_or_none(id=verification_id)
        if verification and verification.user_id != user.id:
            await NotificationRepository().create(
                recipient_id=verification.user_id,
                actor_id=user.id,
                notification_type=NotificationType.LIKE,
                target_type="VERIFICATION",
                target_id=verification_id,
                message=f"{user.nickname or '누군가'}님이 내 인증에 좋아요를 눌렀어요.",
            )
    return Response({"liked": liked, "like_count": like_count}, status_code=status.HTTP_200_OK)


@challenge_verifications_router.post(
    "/{verification_id}/reactions/{reaction_id}/replies",
    status_code=status.HTTP_201_CREATED,
)
async def create_reply(
    verification_id: int,
    reaction_id: int,
    body: ReactionCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ReactionService, Depends(ReactionService)],
) -> Response:
    reply = await service.create_reply(user, verification_id, reaction_id, body.content or "")
    parent = await ChallengeReaction.get_or_none(id=reaction_id)
    if parent and parent.user_id != user.id:
        await NotificationRepository().create(
            recipient_id=parent.user_id,
            actor_id=user.id,
            notification_type=NotificationType.REPLY,
            target_type="COMMENT",
            target_id=reaction_id,
            message=f"{user.nickname or '누군가'}님이 내 댓글에 답글을 남겼어요.",
        )
    return Response(
        ReactionResponse.model_validate(reply).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@challenge_verifications_router.post(
    "/{verification_id}/reactions",
    response_model=ReactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reaction(
    verification_id: int,
    body: ReactionCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ReactionService, Depends(ReactionService)],
) -> Response:
    reaction = await service.create(user, verification_id, body)
    if body.type == ReactionType.COMMENT:
        verification = await ChallengeVerification.get_or_none(id=verification_id)
        if verification and verification.user_id != user.id:
            await NotificationRepository().create(
                recipient_id=verification.user_id,
                actor_id=user.id,
                notification_type=NotificationType.COMMENT,
                target_type="VERIFICATION",
                target_id=verification_id,
                message=f"{user.nickname or '누군가'}님이 내 인증에 댓글을 남겼어요.",
            )
    return Response(
        ReactionResponse.model_validate(reaction).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@challenge_verifications_router.patch(
    "/{verification_id}/reactions/{reaction_id}",
    response_model=ReactionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_reaction(
    verification_id: int,
    reaction_id: int,
    body: ReactionUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ReactionService, Depends(ReactionService)],
) -> Response:
    reaction = await service.update(user, reaction_id, body)
    return Response(
        ReactionResponse.model_validate(reaction).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@challenge_verifications_router.delete(
    "/{verification_id}/reactions/{reaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reaction(
    verification_id: int,
    reaction_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ReactionService, Depends(ReactionService)],
) -> Response:
    await service.delete(user, reaction_id)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Summaries / Recommendations
# ---------------------------------------------------------------------------


@challenge_summaries_router.get("", response_model=ChallengeSummaryResponse, status_code=status.HTTP_200_OK)
async def get_challenge_summary(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeSummaryService, Depends(ChallengeSummaryService)],
    period: Annotated[str, Query()] = "weekly",
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> Response:
    payload = await service.summarize(user, period, date_from, date_to)
    return Response(payload, status_code=status.HTTP_200_OK)


@challenge_recommendations_router.get(
    "",
    response_model=ChallengeRecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_challenge_recommendations(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeRecommendationService, Depends(ChallengeRecommendationService)],
    prediction_id: Annotated[int, Query(alias="predictionId")],
    limit: Annotated[int, Query(ge=1, le=20)] = 3,
) -> Response:
    items = await service.for_prediction(user, prediction_id, limit)
    payload = ChallengeRecommendationResponse(
        prediction_id=prediction_id,
        items=[ChallengeRecommendationItem.model_validate(it) for it in items],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)
