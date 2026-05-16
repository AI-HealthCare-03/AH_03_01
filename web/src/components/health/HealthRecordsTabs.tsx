"use client";

import { useRouter, useSearchParams } from "next/navigation";

export type HealthTab = "summary" | "detail" | "trend" | "report" | "risk";

const TABS: { id: HealthTab; label: string }[] = [
  { id: "summary", label: "요약" },
  { id: "detail", label: "상세" },
  { id: "trend", label: "추이" },
  { id: "report", label: "월간 리포트" },
  { id: "risk", label: "위험도" },
];

interface HealthRecordsTabsProps {
  activeTab: HealthTab;
}

export default function HealthRecordsTabs({ activeTab }: HealthRecordsTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleTabChange = (tab: HealthTab) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    router.push(`/health-records?${params.toString()}`);
  };

  return (
    <div className="bg-white border-b border-border sticky top-16 z-30 md:top-0">
      <div className="max-w-5xl mx-auto px-4">
        <nav
          className="flex overflow-x-auto scrollbar-hide gap-0 -mb-px"
          aria-label="건강 기록 탭"
          role="tablist"
        >
          {TABS.map(({ id, label }) => {
            const isActive = activeTab === id;
            return (
              <button
                key={id}
                role="tab"
                aria-selected={isActive}
                onClick={() => handleTabChange(id)}
                className={[
                  "flex-shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                  isActive
                    ? "border-brand-black text-text-primary"
                    : "border-transparent text-text-secondary hover:text-text-primary",
                ].join(" ")}
              >
                {label}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
