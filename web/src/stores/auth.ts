import { create } from "zustand";
import { getToken, setToken, removeToken } from "@/lib/tokens";

export const ACTIVE_USER_KEY = "active-user-id";

function decodeUserId(token: string): string {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - b64.length % 4) % 4);
    const payload = JSON.parse(atob(padded));
    return String(payload.user_id ?? "");
  } catch { return ""; }
}

/* =========================================
   인증 상태 Zustand 스토어
   ========================================= */

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;

  /* 액션 */
  setAuth: (token: string) => void;
  clearAuth: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,

  /** 로그인 성공 후 토큰 저장 */
  setAuth: (token: string) => {
    setToken(token);
    const userId = decodeUserId(token);
    if (userId) localStorage.setItem(ACTIVE_USER_KEY, userId);
    set({ token, isAuthenticated: true });
  },

  /** 로그아웃 시 토큰 삭제 */
  clearAuth: () => {
    removeToken();
    localStorage.removeItem(ACTIVE_USER_KEY);
    set({ token: null, isAuthenticated: false });
  },

  /** SSR → CSR 전환 시 localStorage 에서 토큰 복원 */
  hydrate: () => {
    const token = getToken();
    if (token) {
      const userId = decodeUserId(token);
      if (userId) localStorage.setItem(ACTIVE_USER_KEY, userId);
      set({ token, isAuthenticated: true });
    }
  },
}));
