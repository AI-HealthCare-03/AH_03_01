import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useInventoryItemApi } from "@/lib/api/pets";
import { INVENTORY_KEY } from "./useInventory";
import { MY_PET_QUERY_KEY } from "./useMyPet";

export function useUseInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inventoryId: number) => useInventoryItemApi(inventoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: INVENTORY_KEY });
      qc.invalidateQueries({ queryKey: MY_PET_QUERY_KEY });
    },
  });
}
