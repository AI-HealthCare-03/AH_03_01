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
    VerificationCreateRequest,
    VerificationListResponse,
    VerificationResponse,
    VerificationUpdateRequest,
)
from app.models.challenge import (
    ChallengeCategory,
    ChallengeScope,
    ChallengeStatus,
    VerificationMethod,
    VerificationStatus,
)
from app.models.users import User
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
    keyword: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    mine: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Response:
    items, total = await service.list_challenges(
        user=user,
        scope=scope.value if scope else None,
        challenge_status=challenge_status.value if challenge_status else None,
        category=category.value if category else None,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
        mine_only=mine,
    )
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
                status=ch.status,
                category=ch.category,
                start_date=ch.start_date,
                end_date=ch.end_date,
            )
            for ch in items
        ],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@challenges_router.get("/{challenge_id}", response_model=ChallengeResponse, status_code=status.HTTP_200_OK)
async def get_challenge(
    challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChallengeService, Depends(ChallengeService)],
) -> Response:
    challenge = await service.get_owned_or_participating(user, challenge_id)
    payload = ChallengeResponse.model_validate(challenge).model_dump()
    # 그룹 챌린지의 경우 참여자/방장에게 invite_code 노출 (코드 복사 기능)
    if challenge.scope.value == "GROUP":
        invite_code = await service.get_active_invite_code(challenge.id)
        if invite_code:
            payload["invite_code"] = invite_code
    return Response(payload, status_code=status.HTTP_200_OK)


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
    participants = await service.list_participants(user, challenge_id)
    payload = [ParticipantResponse.model_validate(p).model_dump() for p in participants]
    return Response({"participants": payload}, status_code=status.HTTP_200_OK)


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
        if not code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invite_code 가 필요합니다.")
        participant = await service.join_by_code(user, challenge_id, code)
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
    verification = await service.create(user, body)
    return Response(
        VerificationResponse.model_validate(verification).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


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
    verification, comments = await service.list(user, verification_id)
    payload = ReactionListResponse(
        like_count=verification.like_count,
        comments=[ReactionResponse.model_validate(c) for c in comments],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


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
    limit: Annotated[int, Query(ge=1, le=5)] = 3,
) -> Response:
    items = await service.for_prediction(user, prediction_id, limit)
    payload = ChallengeRecommendationResponse(
        prediction_id=prediction_id,
        items=[ChallengeRecommendationItem.model_validate(it) for it in items],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)
