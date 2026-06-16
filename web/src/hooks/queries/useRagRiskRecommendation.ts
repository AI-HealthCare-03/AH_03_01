/* =========================================
   RAG 위험도 권고 React Query 훅
   POST /api/v1/risk-recommendations — body 없음, JWT 인증
   캐시는 백엔드 투명 처리. 프론트는 enabled 될 때마다 POST.
   ========================================= */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchRagRiskRecommendation } from "@/lib/api/health";
import { pushNotification } from "@/components/layout/NotificationDropdown";
import { riskLevelCacheKey } from "@/lib/notifKeys";
import type { RagRiskRecommendationResponse } from "@/types/health";

export const RAG_RISK_RECOMMENDATION_KEY = ["rag-risk-recommendation"] as const;

const DISEASE_LABELS: Record<string, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
};

const RISK_LABELS: Record<string, string> = {
  NORMAL: "정상",
  CAUTION: "주의",
  RISK: "위험",
  HIGH_RISK: "고위험",
};

export function useRagRiskRecommendation() {
  const queryClient = useQueryClient();

  return useMutation<RagRiskRecommendationResponse, unknown, void>({
    mutationFn: () => fetchRagRiskRecommendation(),
    onSuccess: (data) => {
      // 응답을 쿼리 캐시에도 저장해 AiSuggestions 에서 읽을 수 있게 한다.
      queryClient.setQueryData(RAG_RISK_RECOMMENDATION_KEY, data);

      // 위험도 변화 알림: 이전 risk_level 과 비교 후 변화한 질환만 알림 push
      if (data.predictions?.length) {
        try {
          const prevRaw = localStorage.getItem(riskLevelCacheKey());
          const prevMap: Record<string, string> = prevRaw ? JSON.parse(prevRaw) : {};
          const nextMap: Record<string, string> = { ...prevMap };

          for (const pred of data.predictions) {
            const prev = prevMap[pred.disease_type];
            if (prev && prev !== pred.risk_level) {
              pushNotification({
                category: "위험도",
                title: `${DISEASE_LABELS[pred.disease_type] ?? pred.disease_type} 위험도 변화`,
                body: `${RISK_LABELS[prev] ?? prev}에서 ${RISK_LABELS[pred.risk_level] ?? pred.risk_level}(으)로 변했습니다.`,
              });
            }
            nextMap[pred.disease_type] = pred.risk_level;
          }

          localStorage.setItem(riskLevelCacheKey(), JSON.stringify(nextMap));
        } catch { /* 무시 */ }
      }
    },
  });
}
