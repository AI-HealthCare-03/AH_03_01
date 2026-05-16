/* =========================================
   오늘 출석 체크 mutation 훅
   성공 시 attendance-month 캐시 무효화
   ========================================= */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { postAttendanceCheck } from "@/lib/api/home";
import { ATTENDANCE_MONTH_KEY } from "./useAttendanceMonth";

export function useCheckInToday() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: postAttendanceCheck,
    onSuccess: () => {
      /* 출석 관련 모든 캐시 무효화 */
      queryClient.invalidateQueries({ queryKey: ATTENDANCE_MONTH_KEY });
    },
  });
}
