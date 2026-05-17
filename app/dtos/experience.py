from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class WeeklyXpBreakdownItem(BaseModel):
    kind: str
    count: int
    points: int


class WeeklyXpResponse(BaseModel):
    week_id: str
    total_points: int
    items: list[WeeklyXpBreakdownItem]


class LeaderboardEntryDto(BaseModel):
    user_id: UUID
    user_name: str
    points: int
    rank: int


class LeaderboardResponse(BaseModel):
    week_id: str
    entries: list[LeaderboardEntryDto]
    my_rank: int | None
    my_points: int
