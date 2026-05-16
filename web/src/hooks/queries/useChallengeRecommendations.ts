/* =========================================
   추천 챌린지 React Query 훅
   predictionId가 없으면 비활성화
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchChallengeRecommendations } from "@/lib/api/home";

export const CHALLENGE_RECOMMENDATIONS_KEY = ["challenge-recommendations"] as const;

export function useChallengeRecommendations(
  predictionId: number | undefined,
  limit = 3
) {
  return useQuery({
    queryKey: [...CHALLENGE_RECOMMENDATIONS_KEY, predictionId, limit],
    queryFn: () => fetchChallengeRecommendations(predictionId!, limit),
    enabled: !!predictionId,
  });
}
