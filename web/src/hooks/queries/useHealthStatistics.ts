import { useQuery } from "@tanstack/react-query";
import { fetchHealthStatistics } from "@/lib/api/health";
import type { StatPeriod } from "@/types/health";

export const HEALTH_STATISTICS_KEY = "health-statistics";

export function useHealthStatistics(params: {
  metric: string;
  subType?: string;
  period?: StatPeriod;
  limit?: number;
}) {
  return useQuery({
    queryKey: [HEALTH_STATISTICS_KEY, params],
    queryFn: () => fetchHealthStatistics(params),
    enabled: !!params.metric,
  });
}
