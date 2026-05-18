/* =========================================
   내 펫 React Query 훅 (404 → null)
   ========================================= */

import { useQuery } from "@tanstack/react-query";
import { fetchMyPet } from "@/lib/api/home";

export const MY_PET_QUERY_KEY = ["my-pet"] as const;

export function useMyPet() {
  return useQuery({
    queryKey: MY_PET_QUERY_KEY,
    queryFn: fetchMyPet,
    /* 가방에서 아이템 사용 후 뒤로가기 시 캐시가 stale 인 채로 보이는 문제 방지.
       마운트마다 / 윈도우 포커스마다 자동 재조회 한다. */
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    staleTime: 0,
  });
}
