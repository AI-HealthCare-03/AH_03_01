/* =========================================
   주간 활동량(EXP) API
   ========================================= */

import apiClient from "./client";
import type { WeeklyXpResponse, LeaderboardResponse } from "@/types/experience";

export async function fetchWeeklyXp(): Promise<WeeklyXpResponse> {
  const { data } = await apiClient.get<WeeklyXpResponse>(
    "/api/v1/users/me/weekly-xp",
  );
  return data;
}

export async function fetchWeeklyLeaderboard(
  limit = 10,
  weekId?: string,
): Promise<LeaderboardResponse> {
  const params: Record<string, string | number> = { limit };
  if (weekId) params.weekId = weekId;
  const { data } = await apiClient.get<LeaderboardResponse>(
    "/api/v1/leaderboards/weekly",
    { params },
  );
  return data;
}
