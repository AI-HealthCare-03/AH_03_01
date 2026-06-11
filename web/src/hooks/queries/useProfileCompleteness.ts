/* =========================================
   건강 프로필 완성도 React Query 훅
   GET /api/v1/health-records?recordType=profile → completeness 필드
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchProfileCompleteness } from "@/lib/api/health";

export const PROFILE_COMPLETENESS_KEY = ["profile-completeness"] as const;

export function useProfileCompleteness() {
  return useQuery({
    queryKey: PROFILE_COMPLETENESS_KEY,
    queryFn: fetchProfileCompleteness,
  });
}
