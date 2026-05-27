/* =========================================
   펫 API
   ========================================= */

import apiClient from "./client";
import type { MyPet, StoreItemsResponse, InventoryListResponse, PurchaseResponse, InventoryUseResponse, ItemCategory } from "@/types/api";

export type PetType = "DOG" | "CAT" | "PLANT";
export type PetStyleKey = "MALTIPOO" | "RAGDOLL" | "SUCCULENT";

/** PetType ↔ 스타일 매핑 (UI 측 합의) */
export const STYLE_TO_TYPE: Record<PetStyleKey, PetType> = {
  MALTIPOO: "DOG",
  RAGDOLL: "CAT",
  SUCCULENT: "PLANT",
};

export interface CreatePetRequest {
  name: string;
  pet_type: PetType;
  selected_style: PetStyleKey;
}

export async function createPet(body: CreatePetRequest): Promise<MyPet> {
  const { data } = await apiClient.post<MyPet>("/api/v1/pets", body);
  return data;
}

export async function fetchStoreItems(category?: ItemCategory): Promise<StoreItemsResponse> {
  const { data } = await apiClient.get<StoreItemsResponse>("/api/v1/store/items", { params: category ? { category } : {} });
  return data;
}

export async function purchaseStoreItem(body: { item_id: number; quantity: number }): Promise<PurchaseResponse> {
  const { data } = await apiClient.post<PurchaseResponse>("/api/v1/store/purchases", body);
  return data;
}

export async function fetchInventory(category?: ItemCategory): Promise<InventoryListResponse> {
  const { data } = await apiClient.get<InventoryListResponse>("/api/v1/inventory", { params: category ? { category } : {} });
  return data;
}

export async function consumeInventoryItems(inventoryId: number): Promise<InventoryUseResponse> {
  const { data } = await apiClient.post<InventoryUseResponse>(`/api/v1/inventory/${inventoryId}/use`);
  return data;
}
