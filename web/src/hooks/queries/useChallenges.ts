import { useQuery } from "@tanstack/react-query";
import { fetchChallenges } from "@/lib/api/challenge";
import type { ChallengeStatus, ChallengeScope } from "@/types/challenge";

export const CHALLENGES_KEY = "challenges" as const;

export function useChallenges(params: {
  mine?: boolean;
  leftOnly?: boolean;
  status?: ChallengeStatus;
  scope?: ChallengeScope;
  category?: string;
  visibility?: string;
  size?: number;
  page?: number;
  from?: string;
  to?: string;
  sortBy?: "created_at" | "end_date";
  enabled?: boolean;
}) {
  const { enabled = true, ...fetchParams } = params;
  return useQuery({
    queryKey: [CHALLENGES_KEY, fetchParams],
    queryFn: () => fetchChallenges(fetchParams),
    enabled,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    staleTime: 0,
  });
}
