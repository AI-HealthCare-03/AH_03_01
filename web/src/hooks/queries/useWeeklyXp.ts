"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchWeeklyLeaderboard, fetchWeeklyXp } from "@/lib/api/experience";

export const WEEKLY_XP_KEY = ["weekly-xp"] as const;
export const WEEKLY_LEADERBOARD_KEY = ["weekly-leaderboard"] as const;

export function useWeeklyXp() {
  return useQuery({
    queryKey: WEEKLY_XP_KEY,
    queryFn: fetchWeeklyXp,
    staleTime: 60_000,
  });
}

export function useWeeklyLeaderboard(limit = 10) {
  return useQuery({
    queryKey: [...WEEKLY_LEADERBOARD_KEY, limit] as const,
    queryFn: () => fetchWeeklyLeaderboard(limit),
    staleTime: 60_000,
  });
}
