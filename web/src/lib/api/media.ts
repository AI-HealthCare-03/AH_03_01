import { API_BASE_URL } from "@/constants";

/* =========================================
   백엔드가 반환하는 미디어 URL 정규화.
   - 이미 절대 URL(http/https) 이면 그대로
   - 상대경로(/media/...) 면 API 호스트 prefix 부착
   - falsy 이면 undefined
   ========================================= */
export function resolveMediaUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}
