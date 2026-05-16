/* =========================================
   단일 측정 통계 React Query 훅
   metric: blood_pressure | blood_glucose | hba1c
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchMetricStat } from "@/lib/api/home";

export const METRIC_STAT_KEY = ["metric-stat"] as const;

export function useMetricStat(metric: string, subType?: string) {
  return useQuery({
    queryKey: [...METRIC_STAT_KEY, metric, subType],
    queryFn: () => fetchMetricStat(metric, subType),
  });
}
