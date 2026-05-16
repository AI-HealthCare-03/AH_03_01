import { useQuery } from "@tanstack/react-query";
import { fetchMonthlyReport } from "@/lib/api/health";

export const MONTHLY_REPORT_KEY = "monthly-report";

export function useMonthlyReport(month: string /* YYYY-MM */) {
  return useQuery({
    queryKey: [MONTHLY_REPORT_KEY, month],
    queryFn: () => fetchMonthlyReport(month),
    enabled: !!month,
  });
}
