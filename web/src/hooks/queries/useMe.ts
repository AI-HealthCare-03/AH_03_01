/* =========================================
   내 정보 React Query 훅
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/lib/api/home";

export const ME_QUERY_KEY = ["me"] as const;

export function useMe() {
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: fetchMe,
  });
}
