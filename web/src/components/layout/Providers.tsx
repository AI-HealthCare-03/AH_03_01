"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { ToastProvider } from "@/components/ui/Toast";

/* =========================================
   Providers — 클라이언트 컴포넌트 전용
   ========================================= */

interface ProvidersProps {
  children: ReactNode;
}

export default function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            gcTime: 10 * 60 * 1000, // 캐시를 10분 보존 → 페이지 이동 시 즉시 표시
            retry: 1,
            refetchOnWindowFocus: false,
            refetchOnMount: false, // 캐시 데이터가 fresh 하면 마운트 시 재요청 안 함
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
