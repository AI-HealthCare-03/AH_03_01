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
  });
}
