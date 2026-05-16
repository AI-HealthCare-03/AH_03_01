/* =========================================
   최신 질병 예측 결과 React Query 훅
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchLatestPredictions } from "@/lib/api/home";

export const LATEST_PREDICTIONS_KEY = ["latest-predictions"] as const;

export function useLatestPredictions() {
  return useQuery({
    queryKey: LATEST_PREDICTIONS_KEY,
    queryFn: fetchLatestPredictions,
  });
}
