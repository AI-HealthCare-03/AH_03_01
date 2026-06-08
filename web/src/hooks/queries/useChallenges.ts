import { useQuery } from "@tanstack/react-query";
import { fetchChallenges } from "@/lib/api/challenge";
import type { ChallengeStatus, ChallengeScope } from "@/types/challenge";

export const CHALLENGES_KEY = "challenges" as const;

export function useChallenges(params: {
  mine?: boolean;
  status?: ChallengeStatus;
  scope?: ChallengeScope;
  size?: number;
  page?: number;
  from?: string;
  to?: string;
  sortBy?: "start_date" | "end_date";
}) {
  return useQuery({
    queryKey: [CHALLENGES_KEY, params],
    queryFn: () => fetchChallenges(params),
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    staleTime: 0,
  });
}
