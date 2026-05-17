/* =========================================
   펫 API
   ========================================= */

import apiClient from "./client";
import type { MyPet } from "@/types/api";

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
