"""주간 활동량(EXP) + 리더보드 API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies.security import get_request_user
from app.dtos.experience import (
    LeaderboardEntryDto,
    LeaderboardResponse,
    WeeklyXpBreakdownItem,
    WeeklyXpResponse,
)
from app.models.users import User
from app.services.experience import ExperienceService, previous_week_id

experience_router = APIRouter(prefix="/users/me", tags=["experience"])
leaderboard_router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


@experience_router.get("/weekly-xp", response_model=WeeklyXpResponse, status_code=status.HTTP_200_OK)
async def get_my_weekly_xp(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ExperienceService, Depends(ExperienceService)],
) -> Response:
    # 지나간 주차 정산을 lazy 처리
    await service.settle_week_if_needed(week_id=previous_week_id())
    summary = await service.get_weekly_summary(user_id=user.id)
    payload = WeeklyXpResponse(
        week_id=summary.week_id,
        total_points=summary.total_points,
        items=[WeeklyXpBreakdownItem(kind=i.kind, count=i.count, points=i.points) for i in summary.items],
    )
    return Response(payload.model_dump_json(), status_code=status.HTTP_200_OK, media_type="application/json")


@leaderboard_router.get("/weekly", response_model=LeaderboardResponse, status_code=status.HTTP_200_OK)
async def get_weekly_leaderboard(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ExperienceService, Depends(ExperienceService)],
    week_id: Annotated[str | None, Query(alias="weekId")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> Response:
    await service.settle_week_if_needed(week_id=previous_week_id())
    result = await service.get_leaderboard(week_id=week_id, my_user_id=user.id, limit=limit)
    payload = LeaderboardResponse(
        week_id=result.week_id,
        entries=[
            LeaderboardEntryDto(
                user_id=e.user_id, user_name=e.user_name, points=e.points, rank=e.rank
            )
            for e in result.entries
        ],
        my_rank=result.my_rank,
        my_points=result.my_points,
    )
    return Response(payload.model_dump_json(), status_code=status.HTTP_200_OK, media_type="application/json")
