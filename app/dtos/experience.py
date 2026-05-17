from __future__ import annotations

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
    user_id: int
    user_name: str
    points: int
    rank: int


class LeaderboardResponse(BaseModel):
    week_id: str
    entries: list[LeaderboardEntryDto]
    my_rank: int | None
    my_points: int
