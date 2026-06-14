import { useQuery } from "@tanstack/react-query";
import {
  fetchMonthlyReport,
  fetchMonthlyReportV2,
  fetchMonthlyReportV2Range,
} from "@/lib/api/health";

export const MONTHLY_REPORT_KEY = "monthly-report";
export const MONTHLY_REPORT_V2_KEY = "monthly-report-v2";
export const MONTHLY_REPORT_V2_RANGE_KEY = "monthly-report-v2-range";

export function useMonthlyReport(month: string /* YYYY-MM */) {
  return useQuery({
    queryKey: [MONTHLY_REPORT_KEY, month],
    queryFn: () => fetchMonthlyReport(month),
    enabled: !!month,
  });
}

export function useMonthlyReportV2(month: string /* YYYY-MM */, enabled = true) {
  return useQuery({
    queryKey: [MONTHLY_REPORT_V2_KEY, month],
    queryFn: () => fetchMonthlyReportV2(month),
    enabled: enabled && !!month,
  });
}

export function useMonthlyReportV2Range(
  dateFrom: string /* YYYY-MM-DD */,
  dateTo: string /* YYYY-MM-DD */,
  enabled = true
) {
  return useQuery({
    queryKey: [MONTHLY_REPORT_V2_RANGE_KEY, dateFrom, dateTo],
    queryFn: () => fetchMonthlyReportV2Range(dateFrom, dateTo),
    enabled: enabled && !!dateFrom && !!dateTo,
  });
}
