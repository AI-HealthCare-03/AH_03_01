"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";

/**
 * /predictions — 홈의 "위험도 자세히 보기" 링크 대응
 * latest 예측 ID 를 찾아 /health-records?tab=risk 로 리다이렉트.
 * 예측이 없으면 바로 risk 탭으로 이동 (빈 상태 UI 처리는 RiskTab에서).
 */

export default function PredictionsIndexPage() {
  const router = useRouter();
  const { data, isLoading } = useLatestPredictions();

  useEffect(() => {
    if (isLoading) return;
    router.replace("/health-records?tab=risk");
  }, [isLoading, data, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-full border-4 border-brand border-t-transparent animate-spin" />
        <p className="text-sm text-text-secondary">위험도 분석 페이지로 이동 중...</p>
      </div>
    </div>
  );
}
