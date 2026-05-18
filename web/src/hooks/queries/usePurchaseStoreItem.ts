import { useMutation, useQueryClient } from "@tanstack/react-query";
import { purchaseStoreItem } from "@/lib/api/pets";
import { POINT_BALANCE_KEY } from "./usePointBalance";
import { INVENTORY_KEY } from "./useInventory";

export function usePurchaseStoreItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: purchaseStoreItem,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: POINT_BALANCE_KEY });
      qc.invalidateQueries({ queryKey: INVENTORY_KEY });
    },
  });
}
