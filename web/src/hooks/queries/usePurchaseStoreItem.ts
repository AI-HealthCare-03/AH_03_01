import { useMutation, useQueryClient } from "@tanstack/react-query";
import { purchaseStoreItem } from "@/lib/api/pets";
import { POINT_BALANCE_KEY } from "./usePointBalance";
import { INVENTORY_KEY } from "./useInventory";

export function usePurchaseStoreItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: purchaseStoreItem,
    onSuccess: () => {
      // refetchType:"all" → 비활성(미마운트) 쿼리도 즉시 재요청.
      // 전역 refetchOnMount:false 라서 이게 없으면 가방 이동 시 옛 캐시가 보인다.
      qc.invalidateQueries({ queryKey: POINT_BALANCE_KEY, refetchType: "all" });
      qc.invalidateQueries({ queryKey: INVENTORY_KEY, refetchType: "all" });
    },
  });
}
