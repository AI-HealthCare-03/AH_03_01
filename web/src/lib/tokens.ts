import { TOKEN_KEY } from "@/constants";

/* =========================================
   토큰 저장/조회/삭제 유틸
   localStorage 기반 (추후 httpOnly cookie 로 이전 가능)
   ========================================= */

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
