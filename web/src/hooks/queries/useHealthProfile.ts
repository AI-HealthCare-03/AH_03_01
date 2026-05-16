/* =========================================
   건강 프로필(신장·체중) React Query 훅
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchHealthProfile } from "@/lib/api/home";

export const HEALTH_PROFILE_KEY = ["health-profile"] as const;

export function useHealthProfile() {
  return useQuery({
    queryKey: HEALTH_PROFILE_KEY,
    queryFn: fetchHealthProfile,
  });
}
