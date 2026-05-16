"use client";

import { useState } from "react";
import { useHealthStatistics } from "@/hooks/queries/useHealthStatistics";
import { useHealthProfile } from "@/hooks/queries/useHealthProfile";
import BPTrendChart from "./charts/BPTrendChart";
import BGTrendChart from "./charts/BGTrendChart";
import HbA1cBarChart from "./charts/HbA1cBarChart";
import WeightTrendChart from "./charts/WeightTrendChart";
import type { StatPeriod, HealthProfileDetail } from "@/types/health";

/* ── 상수 ──────────────────────────────── */

type SubTab = "bp" | "glucose" | "hba1c" | "weight";

const SUB_TABS: { id: SubTab; label: string }[] = [
  { id: "bp", label: "혈압" },
  { id: "glucose", label: "혈당" },
  { id: "hba1c", label: "HbA1c" },
  { id: "weight", label: "체중·BMI" },
];

const PERIODS: { id: StatPeriod; label: string }[] = [
  { id: "1w", label: "1주" },
  { id: "1m", label: "1개월" },
  { id: "3m", label: "3개월" },
  { id: "6m", label: "6개월" },
];

const MIN_DATA_COUNT = 3;

/* ── 빈 상태 ────────────────────────────── */

function InsufficientDataNotice() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <span className="text-4xl">📉</span>
      <p className="font-semibold text-text-primary">데이터가 부족합니다</p>
      <p className="text-sm text-text-secondary text-center">
        최소 3회 이상 측정이 필요합니다.
        <br />
        꾸준히 기록하면 추이를 확인할 수 있어요.
      </p>
    </div>
  );
}

/* ── 사이드 통계 (데스크탑) ─────────────── */

interface StatSideCardProps {
  subTab: SubTab;
  series: { primary_value: string; secondary_value?: string | null }[];
  peerAverage?: {
    primary_value: number;
    secondary_value?: number;
    label: string;
  } | null;
}

function StatSideCard({ subTab, series, peerAverage }: StatSideCardProps) {
  if (series.length === 0) return null;

  const primaryValues = series.map((s) => parseFloat(s.primary_value));
  const avg = primaryValues.reduce((a, b) => a + b, 0) / primaryValues.length;
  const max = Math.max(...primaryValues);
  const min = Math.min(...primaryValues);

  const secondaryValues = series
    .filter((s) => s.secondary_value)
    .map((s) => parseFloat(s.secondary_value!));
  const diaAvg =
    secondaryValues.length > 0
      ? secondaryValues.reduce((a, b) => a + b, 0) / secondaryValues.length
      : null;

  const unitMap: Record<SubTab, string> = {
    bp: "mmHg",
    glucose: "mg/dL",
    hba1c: "%",
    weight: "kg",
  };
  const unit = unitMap[subTab];

  return (
    <div className="hidden md:block w-56 shrink-0">
      <div className="bg-white rounded-[16px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-3">
        <h3 className="font-bold text-sm text-text-primary">통계 요약</h3>

        {subTab === "bp" && diaAvg !== null && (
          <>
            <StatRow label="평균 수축기" value={`${avg.toFixed(0)} ${unit}`} />
            <StatRow label="평균 이완기" value={`${diaAvg.toFixed(0)} ${unit}`} />
          </>
        )}
        {subTab !== "bp" && (
          <StatRow label="평균" value={`${avg.toFixed(1)} ${unit}`} />
        )}

        <StatRow label="최고" value={`${max.toFixed(subTab === "hba1c" ? 1 : 0)} ${unit}`} />
        <StatRow label="최저" value={`${min.toFixed(subTab === "hba1c" ? 1 : 0)} ${unit}`} />
        <StatRow label="측정 횟수" value={`${series.length}회`} />

        {peerAverage && (
          <div className="pt-2 border-t border-border">
            <p className="text-xs text-text-tertiary mb-1">동연령 평균</p>
            <p className="text-sm font-semibold text-text-primary">
              {peerAverage.label}: {peerAverage.primary_value.toFixed(subTab === "hba1c" ? 1 : 0)} {unit}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-text-secondary">{label}</span>
      <span className="font-semibold text-text-primary">{value}</span>
    </div>
  );
}

/* ── 혈압 패널 ──────────────────────────── */

function BPPanel({ period }: { period: StatPeriod }) {
  const { data, isLoading } = useHealthStatistics({ metric: "BLOOD_PRESSURE", period });

  if (isLoading) return <ChartSkeleton />;
  const series = data?.series ?? [];
  const insufficient = series.length < MIN_DATA_COUNT;

  return (
    <div className="flex gap-4">
      <div className="flex-1 min-w-0">
        {insufficient ? <InsufficientDataNotice /> : <BPTrendChart series={series} />}
      </div>
      {!insufficient && (
        <StatSideCard
          subTab="bp"
          series={series}
          peerAverage={data?.peer_average}
        />
      )}
    </div>
  );
}

/* ── 혈당 패널 ──────────────────────────── */

function GlucosePanel({ period }: { period: StatPeriod }) {
  const { data: fastingData, isLoading: l1 } = useHealthStatistics({
    metric: "BLOOD_GLUCOSE",
    subType: "FASTING",
    period,
  });
  const { data: postmealData, isLoading: l2 } = useHealthStatistics({
    metric: "BLOOD_GLUCOSE",
    subType: "POSTMEAL",
    period,
  });

  if (l1 || l2) return <ChartSkeleton />;

  const fastingSeries = fastingData?.series ?? [];
  const postmealSeries = postmealData?.series ?? [];
  const insufficient = fastingSeries.length < MIN_DATA_COUNT && postmealSeries.length < MIN_DATA_COUNT;

  return (
    <div className="flex gap-4">
      <div className="flex-1 min-w-0">
        {insufficient ? (
          <InsufficientDataNotice />
        ) : (
          <BGTrendChart fastingSeries={fastingSeries} postmealSeries={postmealSeries} />
        )}
      </div>
      {!insufficient && (
        <StatSideCard
          subTab="glucose"
          series={fastingSeries}
          peerAverage={fastingData?.peer_average}
        />
      )}
    </div>
  );
}

/* ── HbA1c 패널 ─────────────────────────── */

function HbA1cPanel({ period }: { period: StatPeriod }) {
  const { data, isLoading } = useHealthStatistics({ metric: "HBA1C", period });

  if (isLoading) return <ChartSkeleton />;
  const series = data?.series ?? [];
  const insufficient = series.length < MIN_DATA_COUNT;

  return (
    <div className="flex gap-4">
      <div className="flex-1 min-w-0">
        {insufficient ? <InsufficientDataNotice /> : <HbA1cBarChart series={series} />}
      </div>
      {!insufficient && (
        <StatSideCard
          subTab="hba1c"
          series={series}
          peerAverage={data?.peer_average}
        />
      )}
    </div>
  );
}

/* ── 체중·BMI 패널 ──────────────────────── */

function WeightPanel({ period }: { period: StatPeriod }) {
  const { data, isLoading: l1 } = useHealthStatistics({ metric: "WEIGHT", period });
  const { data: profile, isLoading: l2 } = useHealthProfile() as {
    data: HealthProfileDetail | null | undefined;
    isLoading: boolean;
  };

  if (l1 || l2) return <ChartSkeleton />;
  const series = data?.series ?? [];
  const insufficient = series.length < MIN_DATA_COUNT;

  return (
    <div className="flex gap-4">
      <div className="flex-1 min-w-0">
        {insufficient ? (
          <InsufficientDataNotice />
        ) : (
          <WeightTrendChart series={series} heightCm={profile?.height_cm} />
        )}
      </div>
      {!insufficient && (
        <StatSideCard subTab="weight" series={series} peerAverage={data?.peer_average} />
      )}
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="animate-pulse h-64 bg-surface rounded-[12px]" />
  );
}

/* ── 메인 컴포넌트 ─────────────────────── */

export default function TrendTab() {
  const [subTab, setSubTab] = useState<SubTab>("bp");
  const [period, setPeriod] = useState<StatPeriod>("1m");

  return (
    <div className="space-y-5">
      {/* 서브탭 */}
      <div className="flex gap-1 bg-surface rounded-[12px] p-1">
        {SUB_TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setSubTab(id)}
            className={[
              "flex-1 py-2 text-sm font-medium rounded-[10px] transition-colors",
              subTab === id
                ? "bg-white text-text-primary shadow-[0_1px_3px_rgba(0,0,0,0.1)]"
                : "text-text-secondary hover:text-text-primary",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 기간 토글 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-tertiary">기간:</span>
        {PERIODS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setPeriod(id)}
            className={[
              "px-3 py-1.5 text-xs font-medium rounded-[8px] border transition-colors",
              period === id
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 차트 영역 */}
      <div className="bg-white rounded-[16px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        {subTab === "bp" && <BPPanel period={period} />}
        {subTab === "glucose" && <GlucosePanel period={period} />}
        {subTab === "hba1c" && <HbA1cPanel period={period} />}
        {subTab === "weight" && <WeightPanel period={period} />}
      </div>

      {/* 면책 */}
      <p className="text-xs text-text-tertiary text-center">
        본 결과는 참고용입니다. 정확한 진단·치료는 의료 전문가에게 문의하세요.
      </p>
    </div>
  );
}
