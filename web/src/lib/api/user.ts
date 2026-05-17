/* =========================================
   사용자 (마이페이지) API
   GET/PATCH /api/v1/users/me, POST /api/v1/users/me/password
   ========================================= */

import apiClient from "./client";
import type { Me } from "@/types/api";

export interface UpdateMeRequest {
  nickname?: string;
  phone_number?: string;
  avatar_file_id?: number | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export async function updateMe(body: UpdateMeRequest): Promise<Me> {
  const { data } = await apiClient.patch<Me>("/api/v1/users/me", body);
  return data;
}

export async function changeMyPassword(
  body: ChangePasswordRequest,
): Promise<void> {
  await apiClient.post("/api/v1/users/me/password", body);
}
