/* =========================================
   진행 중 챌린지 React Query 훅
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchMyActiveChallenges } from "@/lib/api/home";

export const MY_ACTIVE_CHALLENGES_KEY = ["my-active-challenges"] as const;

export function useMyActiveChallenges(size = 5) {
  return useQuery({
    queryKey: [...MY_ACTIVE_CHALLENGES_KEY, size],
    queryFn: () => fetchMyActiveChallenges(size),
  });
}
