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

  /* client.ts 의 request 인터셉터가 FormData 감지 시 Content-Type 을 자동 제거하므로
     axios 가 boundary 포함된 multipart/form-data 헤더를 알아서 설정한다. */
  const { data } = await apiClient.post<UploadedFile>("/api/v1/files", form);
  return data;
}
