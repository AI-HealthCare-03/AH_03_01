import { create } from "zustand";
import { getToken, setToken, removeToken } from "@/lib/tokens";

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
    set({ token, isAuthenticated: true });
  },

  /** 로그아웃 시 토큰 삭제 */
  clearAuth: () => {
    removeToken();
    set({ token: null, isAuthenticated: false });
  },

  /** SSR → CSR 전환 시 localStorage 에서 토큰 복원 */
  hydrate: () => {
    const token = getToken();
    if (token) {
      set({ token, isAuthenticated: true });
    }
  },
}));
