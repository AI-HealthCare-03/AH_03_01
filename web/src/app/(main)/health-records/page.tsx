"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import HealthRecordsTabs, { type HealthTab } from "@/components/health/HealthRecordsTabs";
import SummaryTab from "@/components/health/SummaryTab";
import DetailTab from "@/components/health/DetailTab";
import TrendTab from "@/components/health/TrendTab";
import ReportTab from "@/components/health/ReportTab";
import RiskTab from "@/components/health/RiskTab";

/* ── 탭 콘텐츠 분기 ─────────────────── */

function TabContent({ tab }: { tab: HealthTab }) {
  switch (tab) {
    case "summary": return <SummaryTab />;
    case "detail":  return <DetailTab />;
    case "trend":   return <TrendTab />;
    case "report":  return <ReportTab />;
    case "risk":    return <RiskTab />;
    default:        return <SummaryTab />;
  }
}

/* ── 쿼리 파라미터 읽기 ─────────────── */

const VALID_TABS: HealthTab[] = ["summary", "detail", "trend", "report", "risk"];

function HealthRecordsInner() {
  const searchParams = useSearchParams();
  const raw = searchParams.get("tab") as HealthTab | null;
  const activeTab: HealthTab =
    raw && VALID_TABS.includes(raw) ? raw : "summary";

  return (
    <div className="min-h-screen bg-[#f8f8f8]" id="health-records-layout">
      <HealthRecordsTabs activeTab={activeTab} />
      <div className="max-w-5xl mx-auto px-4 py-5">
        <TabContent tab={activeTab} />
      </div>
    </div>
  );
}

/* ── 페이지 ──────────────────────────── */

export default function HealthRecordsPage() {
  return (
    <Suspense
      fallback={
        <div className="animate-pulse">
          <div className="h-12 bg-white border-b border-border" />
          <div className="max-w-5xl mx-auto px-4 py-5 space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-32 bg-surface rounded-[16px]" />
            ))}
          </div>
        </div>
      }
    >
      <HealthRecordsInner />
    </Suspense>
  );
}
