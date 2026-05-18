"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth";
import { ROUTES } from "@/constants";

/* =========================================
   인증 훅
   ========================================= */

/**
 * 기본 auth 훅 — hydration + router
 */
export function useAuth() {
  const { token, isAuthenticated, setAuth, clearAuth, hydrate } =
    useAuthStore();
  const router = useRouter();
  const qc = useQueryClient();

  /* 최초 마운트 시 localStorage 에서 토큰 복원 */
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  /* 로그아웃 시 React Query 캐시를 완전히 비워 다음 계정 데이터가 섞이지 않게 한다. */
  const logout = () => {
    clearAuth();
    qc.clear();
    router.push(ROUTES.LOGIN);
  };

  return { token, isAuthenticated, setAuth, clearAuth, logout };
}

/**
 * 보호된 라우트 가드 훅
 * 로그인되어 있지 않으면 /login 으로 리다이렉트
 */
export function useRequireAuth() {
  const { isAuthenticated, hydrate } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    hydrate();
    const token = useAuthStore.getState().token;
    if (!token) {
      router.replace(ROUTES.LOGIN);
    }
  }, [hydrate, router]);

  return { isAuthenticated };
}
