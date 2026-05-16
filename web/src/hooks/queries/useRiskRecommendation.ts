import { useQuery } from "@tanstack/react-query";
import { fetchRiskRecommendations } from "@/lib/api/health";

export const RISK_RECOMMENDATION_KEY = "risk-recommendation";

export function useRiskRecommendation(predictionId: number | undefined) {
  return useQuery({
    queryKey: [RISK_RECOMMENDATION_KEY, predictionId],
    queryFn: () => fetchRiskRecommendations(predictionId!),
    enabled: !!predictionId,
  });
}
