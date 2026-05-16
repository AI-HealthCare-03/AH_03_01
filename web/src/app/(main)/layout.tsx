"use client";

import { type ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import GNB from "@/components/layout/GNB";
import { useAuthStore } from "@/stores/auth";
import { ROUTES } from "@/constants";

/* =========================================
   (main) 그룹 레이아웃
   - GNB 포함
   - hydrate 완료 후 토큰 검사 (race condition 방지)
   - 미인증이면 /login 으로 클라이언트 redirect
   ========================================= */

export default function MainLayout({ children }: { children: ReactNode }) {
  const { hydrate, isAuthenticated, token } = useAuthStore();
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    hydrate();
    setHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace(ROUTES.LOGIN);
    }
  }, [hydrated, token, router]);

  /* hydrate 전 또는 토큰 없을 때는 보호된 화면을 그리지 않는다 */
  if (!hydrated || (!isAuthenticated && !token)) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#f8f8f8]">
      <GNB />
      {/* 모바일: 하단 탭바 높이만큼 패딩 */}
      <main className="md:pt-0 pb-16 md:pb-0">{children}</main>
    </div>
  );
}
