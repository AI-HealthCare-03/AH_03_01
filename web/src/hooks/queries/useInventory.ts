import { useQuery } from "@tanstack/react-query";
import { fetchInventory } from "@/lib/api/pets";
import type { ItemCategory } from "@/types/api";

export const INVENTORY_KEY = ["inventory"] as const;

export function useInventory(category?: ItemCategory) {
  return useQuery({ queryKey: [...INVENTORY_KEY, category ?? "ALL"], queryFn: () => fetchInventory(category) });
}
