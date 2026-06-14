import { useQuery } from "@tanstack/react-query";
import { fetchMonthlyReport, fetchMonthlyReportV2 } from "@/lib/api/health";

export const MONTHLY_REPORT_KEY = "monthly-report";
export const MONTHLY_REPORT_V2_KEY = "monthly-report-v2";

export function useMonthlyReport(month: string /* YYYY-MM */) {
  return useQuery({
    queryKey: [MONTHLY_REPORT_KEY, month],
    queryFn: () => fetchMonthlyReport(month),
    enabled: !!month,
  });
}

export function useMonthlyReportV2(month: string /* YYYY-MM */) {
  return useQuery({
    queryKey: [MONTHLY_REPORT_V2_KEY, month],
    queryFn: () => fetchMonthlyReportV2(month),
    enabled: !!month,
  });
}
