/* =========================================
   월간 출석 기록 React Query 훅
   month: "YYYY-MM" 형식
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchAttendanceMonth } from "@/lib/api/home";

export const ATTENDANCE_MONTH_KEY = ["attendance-month"] as const;

export function useAttendanceMonth(month: string) {
  return useQuery({
    queryKey: [...ATTENDANCE_MONTH_KEY, month],
    queryFn: () => fetchAttendanceMonth(month),
    staleTime: 30_000,
  });
}
