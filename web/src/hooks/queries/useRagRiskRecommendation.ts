/* =========================================
   RAG 위험도 권고 React Query 훅
   POST /api/v1/risk-recommendations — body 없음, JWT 인증
   캐시는 백엔드 투명 처리. 프론트는 enabled 될 때마다 POST.
   ========================================= */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchRagRiskRecommendation } from "@/lib/api/health";
import type { RagRiskRecommendationResponse } from "@/types/health";

export const RAG_RISK_RECOMMENDATION_KEY = ["rag-risk-recommendation"] as const;

export function useRagRiskRecommendation() {
  const queryClient = useQueryClient();

  return useMutation<RagRiskRecommendationResponse, unknown, void>({
    mutationFn: () => fetchRagRiskRecommendation(),
    onSuccess: (data) => {
      // 응답을 쿼리 캐시에도 저장해 AiSuggestions 에서 읽을 수 있게 한다.
      queryClient.setQueryData(RAG_RISK_RECOMMENDATION_KEY, data);
    },
  });
}
