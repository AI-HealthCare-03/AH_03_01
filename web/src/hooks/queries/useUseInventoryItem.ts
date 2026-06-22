import { useMutation, useQueryClient } from "@tanstack/react-query";
import { consumeInventoryItems } from "@/lib/api/pets";
import { INVENTORY_KEY } from "./useInventory";
import { MY_PET_QUERY_KEY } from "./useMyPet";

export function useUseInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inventoryId: number) => consumeInventoryItems(inventoryId),
    onSuccess: () => {
      // refetchType:"all" → 비활성 쿼리도 즉시 재요청(전역 refetchOnMount:false 보정).
      qc.invalidateQueries({ queryKey: INVENTORY_KEY, refetchType: "all" });
      qc.invalidateQueries({ queryKey: MY_PET_QUERY_KEY, refetchType: "all" });
    },
  });
}
