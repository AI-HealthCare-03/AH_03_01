/* =========================================
   포인트 잔액 React Query 훅
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchPointBalance } from "@/lib/api/home";

export const POINT_BALANCE_KEY = ["point-balance"] as const;

export function usePointBalance(size = 3) {
  return useQuery({
    queryKey: [...POINT_BALANCE_KEY, size],
    queryFn: () => fetchPointBalance(size),
  });
}
