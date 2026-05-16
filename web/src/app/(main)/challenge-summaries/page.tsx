"use client";

import { useState } from "react";
import Link from "next/link";
import SummaryStats from "@/components/challenges/summary/SummaryStats";
import { useChallengeSummary } from "@/hooks/queries/useChallengeSummary";

/* =========================================
   챌린지 주간/월간 요약 (10-C16 / 10-C17)
   ========================================= */

type PeriodKey = "weekly" | "monthly";

const PERIOD_TABS: { key: PeriodKey; label: string }[] = [
  { key: "weekly", label: "이번 주" },
  { key: "monthly", label: "이번 달" },
];

export default function ChallengeSummariesPage() {
  const [period, setPeriod] = useState<PeriodKey>("weekly");
  const { data, isLoading, error } = useChallengeSummary(period);

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div>
        <Link
          href="/challenges"
          className="text-sm text-text-tertiary hover:text-text-secondary mb-3 inline-block"
        >
          ← 챌린지로
        </Link>
        <h1 className="text-xl font-black text-text-primary">챌린지 요약</h1>
        <p className="text-sm text-text-secondary mt-1">
          기간별 달성 현황을 확인해보세요
        </p>
      </div>

      {/* 기간 탭 */}
      <div
        role="tablist"
        aria-label="요약 기간 선택"
        className="flex gap-1 bg-surface rounded-[12px] p-1"
      >
        {PERIOD_TABS.map(({ key, label }) => (
          <button
            key={key}
            role="tab"
            aria-selected={period === key}
            onClick={() => setPeriod(key)}
            className={[
              "flex-1 py-2 text-sm font-semibold rounded-[10px] transition-all",
              period === key
                ? "bg-white text-text-primary shadow-sm"
                : "text-text-tertiary hover:text-text-secondary",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 콘텐츠 */}
      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {[0, 1].map((i) => (
              <div
                key={i}
                className="h-24 bg-white rounded-[14px] border border-border animate-pulse"
              />
            ))}
          </div>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-20 bg-white rounded-[14px] border border-border animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div className="py-12 text-center bg-white rounded-[16px] border border-dashed border-border">
          <p className="text-3xl mb-3" aria-hidden="true">😢</p>
          <p className="text-sm font-semibold text-text-secondary">
            요약 데이터를 불러오지 못했어요
          </p>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="py-12 text-center bg-white rounded-[16px] border border-dashed border-border">
          <p className="text-3xl mb-3" aria-hidden="true">📊</p>
          <p className="text-sm font-semibold text-text-secondary">
            {period === "weekly" ? "이번 주" : "이번 달"}에 완료된 챌린지가
            없어요
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            챌린지를 시작해 기록을 만들어 보세요!
          </p>
        </div>
      ) : (
        <SummaryStats data={data} />
      )}
    </div>
  );
}
