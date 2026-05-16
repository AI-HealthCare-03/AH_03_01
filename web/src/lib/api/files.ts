/* =========================================
   파일 업로드 API 래퍼
   POST /api/v1/files (multipart/form-data)
   ========================================= */

import apiClient from "./client";

export interface UploadedFile {
  id: number;
  file_type: string;
  original_name: string;
  access_url: string;
  mime_type: string;
  file_size_bytes: number;
  created_at: string;
}

export type UploadPurpose =
  | "profile"
  | "verification"
  | "post"
  | "inquiry"
  | "other";

export async function uploadFile(
  file: File,
  purpose: UploadPurpose = "other",
): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  form.append("purpose", purpose);

  const { data } = await apiClient.post<UploadedFile>("/api/v1/files", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
