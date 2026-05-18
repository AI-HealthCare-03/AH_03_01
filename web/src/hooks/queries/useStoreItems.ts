import { useQuery } from "@tanstack/react-query";
import { fetchStoreItems } from "@/lib/api/pets";
import type { ItemCategory } from "@/types/api";

export const STORE_ITEMS_KEY = ["store-items"] as const;

export function useStoreItems(category?: ItemCategory) {
  return useQuery({ queryKey: [...STORE_ITEMS_KEY, category ?? "ALL"], queryFn: () => fetchStoreItems(category) });
}
