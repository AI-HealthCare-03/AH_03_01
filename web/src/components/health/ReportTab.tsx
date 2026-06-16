"use client";

import { useState } from "react";
import { format, addMonths, subMonths, subDays } from "date-fns";
import { ko } from "date-fns/locale";
import {
  useMonthlyReportV2,
  useMonthlyReportV2Range,
} from "@/hooks/queries/useMonthlyReport";
import { requestMonthlyReportPdf } from "@/lib/api/health";
import { useToast } from "@/components/ui/Toast";
import RiskSemiGauge from "@/components/health/RiskSemiGauge";
import { FACTOR_TOOLTIP } from "@/components/health/RiskTab";
import BPTrendChart from "@/components/health/charts/BPTrendChart";
import BGTrendChart from "@/components/health/charts/BGTrendChart";
import WeightTrendChart from "@/components/health/charts/WeightTrendChart";
import type { RiskGrade } from "@/types/api";
import type {
  ReportDiseaseRisk,
  ReportTopFactor,
  ReportTrend,
  ReportChallenge,
  ReportGoodHabit,
  ReportHeaderStats,
  StatSeriesPoint,
} from "@/types/health";

/* ── 유틸: ReportTrendPoint → StatSeriesPoint 변환 ─── */

function toStatSeries(
  trend: ReportTrend | undefined
): StatSeriesPoint[] {
  if (!trend || trend.series.length === 0) return [];
  return trend.series.map((p) => ({
    measured_at: p.date + "T00:00:00",
    primary_value: String(p.value),
    secondary_value: p.secondary_value != null ? String(p.secondary_value) : null,
  }));
}

/* ── 유틸: RiskLevel → RiskGrade 매핑 ─── */

function toRiskGrade(level: string | null): RiskGrade {
  if (!level) return "NORMAL";
  const map: Record<string, RiskGrade> = {
    NORMAL: "NORMAL",
    CAUTION: "CAUTION",
    RISK: "RISK",
    HIGH_RISK: "HIGH_RISK",
  };
  return map[level] ?? "NORMAL";
}

/* ── 질환 라벨 ─── */

const DISEASE_LABEL: Record<string, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "이상지질혈증",
};

/* ── 카테고리 이모지 ─── */

const CATEGORY_EMOJI: Record<string, string> = {
  EXERCISE: "🏃",
  WATER: "💧",
  SLEEP: "🌙",
  DIET: "🥗",
  NO_SMOKING: "🚭",
  NO_ALCOHOL: "🚫",
  DISEASE_CARE: "💊",
  MEDITATION: "🧘",
};

/* ── 챌린지 상태 뱃지 ─── */

const CHALLENGE_STATUS_STYLE: Record<
  string,
  { label: string; bg: string; text: string }
> = {
  success: { label: "성공", bg: "bg-green-100", text: "text-green-700" },
  in_progress: { label: "진행중", bg: "bg-yellow-100", text: "text-yellow-700" },
  failed: { label: "실패", bg: "bg-red-100", text: "text-red-600" },
};

/* ── direction 색상 ─── */

function directionColor(direction: string | null): string {
  if (!direction) return "text-text-secondary";
  if (direction.includes("↑") || direction.includes("위험 증가"))
    return "text-status-danger";
  if (direction.includes("↓") || direction.includes("위험 감소"))
    return "text-status-info";
  return "text-text-secondary";
}

/* =========================================================
   섹션 컴포넌트들
   ========================================================= */

/* ── 1. 월 네비게이션 ─── */

interface MonthNavProps {
  current: Date;
  onPrev: () => void;
  onNext: () => void;
}

function MonthNav({ current, onPrev, onNext }: MonthNavProps) {
  const isCurrentMonth =
    format(current, "yyyy-MM") === format(new Date(), "yyyy-MM");
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onPrev}
          className="w-9 h-9 flex items-center justify-center rounded-[8px] hover:bg-surface transition-colors"
          aria-label="이전 달"
        >
          ◀
        </button>
        <span className="font-bold text-lg text-text-primary">
          {format(current, "yyyy년 M월", { locale: ko })}
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={isCurrentMonth}
          className="w-9 h-9 flex items-center justify-center rounded-[8px] hover:bg-surface transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="다음 달"
        >
          ▶
        </button>
      </div>
    </div>
  );
}

/* ── 조회 모드 토글 (월 단위 / 기간 지정) ─── */

type ReportMode = "monthly" | "custom";

function ModeToggle({
  mode,
  onChange,
}: {
  mode: ReportMode;
  onChange: (m: ReportMode) => void;
}) {
  const tabs: { key: ReportMode; label: string }[] = [
    { key: "monthly", label: "월 단위" },
    { key: "custom", label: "기간 지정" },
  ];
  return (
    <div className="inline-flex rounded-[8px] border border-border bg-surface p-0.5">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          onClick={() => onChange(t.key)}
          aria-pressed={mode === t.key}
          className={`px-3 py-1.5 text-xs font-medium rounded-[6px] transition-colors ${
            mode === t.key
              ? "bg-white text-text-primary shadow-[0_1px_2px_rgba(0,0,0,0.1)]"
              : "text-text-secondary"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ── 임의 기간 선택 (date_from ~ date_to) ─── */

function RangePicker({
  from,
  to,
  onFrom,
  onTo,
}: {
  from: string;
  to: string;
  onFrom: (v: string) => void;
  onTo: (v: string) => void;
}) {
  const today = format(new Date(), "yyyy-MM-dd");
  const invalid = !!from && !!to && from > to;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={from}
          max={to || today}
          onChange={(e) => onFrom(e.target.value)}
          aria-label="시작일"
          className="px-2 py-1.5 text-sm border border-border rounded-[8px] bg-white text-text-primary"
        />
        <span className="text-text-tertiary">~</span>
        <input
          type="date"
          value={to}
          min={from || undefined}
          max={today}
          onChange={(e) => onTo(e.target.value)}
          aria-label="종료일"
          className="px-2 py-1.5 text-sm border border-border rounded-[8px] bg-white text-text-primary"
        />
      </div>
      {invalid && (
        <p className="text-xs text-danger">시작일은 종료일보다 이후일 수 없어요.</p>
      )}
    </div>
  );
}

/* ── 2. 헤더 통계 카드 ─── */

function HeaderStatsRow({ stats }: { stats: ReportHeaderStats }) {
  const items = [
    {
      label: "기록한 날",
      value: `${stats.recorded_days}일`,
      always: true,
    },
    {
      label: "평균 수면",
      value:
        stats.avg_sleep_hours != null
          ? `${stats.avg_sleep_hours.toFixed(1)}시간`
          : "데이터 없음",
      always: false,
    },
    {
      label: "걷기 평균",
      value:
        stats.avg_steps != null
          ? `${stats.avg_steps.toLocaleString()}보`
          : "데이터 없음",
      always: false,
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="bg-white rounded-[12px] px-3 py-3 text-center shadow-[0_1px_4px_rgba(0,0,0,0.07)]"
        >
          <p className="text-xs text-text-tertiary mb-1">{item.label}</p>
          <p
            className={[
              "font-bold text-sm",
              item.value === "데이터 없음"
                ? "text-text-tertiary"
                : "text-text-primary",
            ].join(" ")}
          >
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}

/* ── 3. 위험도 예측 결과 섹션 ─── */

const DISEASE_ORDER = ["DIABETES", "HYPERTENSION", "CARDIOVASCULAR"];

function DiseaseRiskSection({ risks }: { risks: ReportDiseaseRisk[] }) {
  if (risks.length === 0) {
    return (
      <SectionCard title="위험도 예측 결과">
        <p className="text-sm text-text-tertiary text-center py-6">
          이번 달 위험도 예측 결과가 없습니다.
        </p>
      </SectionCard>
    );
  }

  const sorted = [...risks].sort(
    (a, b) => DISEASE_ORDER.indexOf(a.disease_type) - DISEASE_ORDER.indexOf(b.disease_type),
  );

  return (
    <SectionCard title="위험도 예측 결과">
      <div className="flex justify-around flex-wrap gap-4">
        {sorted.map((r) => (
          <div key={r.disease_type} className="flex flex-col items-center gap-2">
            <p className="text-xs font-semibold text-text-secondary">
              {DISEASE_LABEL[r.disease_type] ?? r.disease_type}
            </p>
            {/* 라벨은 모델 클래스(risk_level→grade) 기준 — score 백분위 5단계 라벨
                (risk_level_label)은 실제 판정과 어긋나 부정확해 위험도 탭과 동일하게 미사용. */}
            {r.has_prediction && r.risk_score != null ? (
              <RiskSemiGauge
                score={r.risk_score}
                grade={toRiskGrade(r.risk_level)}
                size={120}
              />
            ) : (
              <div className="flex flex-col items-center justify-center w-[120px] h-[86px] rounded-[12px] bg-surface">
                <span className="text-xs text-text-tertiary">예측 없음</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

/* ── 4. 판단 근거 TOP 5 ─── */

const DISEASE_TABS = [
  { key: "DIABETES", label: "당뇨" },
  { key: "HYPERTENSION", label: "고혈압" },
  { key: "CARDIOVASCULAR", label: "이상지질혈증" },
] as const;

function FactorBar({ weight }: { weight: number }) {
  const pct = Math.max(0, Math.min(Math.round(weight * 100), 100));
  return (
    <div className="mt-1 h-1.5 bg-surface rounded-full overflow-hidden">
      <div
        className="h-full bg-brand-black rounded-full transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function TopFactorsSection({ risks }: { risks: ReportDiseaseRisk[] }) {
  const initialTab = risks.find((r) => r.top_factors.length > 0)?.disease_type ?? "HYPERTENSION";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const activeRisk = risks.find((r) => r.disease_type === activeTab);
  const factors: ReportTopFactor[] = (activeRisk?.top_factors ?? [])
    .slice()
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 5);

  return (
    <SectionCard title="판단 근거 TOP 5">
      {/* 탭 */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {DISEASE_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={[
              "shrink-0 px-3 py-1 rounded-full text-xs font-semibold transition-colors",
              activeTab === tab.key
                ? "bg-brand-black text-white"
                : "bg-surface text-text-secondary hover:bg-border",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {factors.length === 0 ? (
        <p className="text-sm text-text-tertiary text-center py-4">
          이번 달 판단 근거 데이터가 없습니다.
        </p>
      ) : (
        <ol className="space-y-3">
          {factors.map((f, i) => {
            const label = f.name_kor ?? f.factor;
            const dirColor = directionColor(f.direction);
            return (
              <li key={f.factor} className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-brand text-brand-black text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary truncate">
                      {label}
                    </span>
                    {f.direction && (
                      <span className={`text-xs font-semibold shrink-0 ${dirColor}`}>
                        {f.direction}
                      </span>
                    )}
                  </div>
                  <FactorBar weight={f.weight} />
                  {/* 변수 산출 방법 설명 — 의료진이 파생 지표를 이해하기 쉽도록 노출. */}
                  {FACTOR_TOOLTIP[f.factor] && (
                    <p className="mt-1 text-[11px] leading-snug text-text-tertiary">
                      {FACTOR_TOOLTIP[f.factor]}
                    </p>
                  )}
                </div>
                <span className="text-xs font-bold text-text-secondary shrink-0 mt-0.5">
                  {(f.weight * 100).toFixed(0)}%
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </SectionCard>
  );
}

/* ── 5. 건강지표 추이 차트 ─── */

const TREND_METRIC_META = {
  blood_pressure: { label: "혈압", unit: "mmHg" },
  blood_glucose: { label: "혈당", unit: "mg/dL" },
  weight: { label: "체중", unit: "kg" },
} as const;

function TrendSummaryBadge({
  label,
  value,
  unit,
}: {
  label: string;
  value: number | null;
  unit: string;
}) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-surface rounded-full text-xs text-text-secondary">
      <span className="font-medium text-text-primary">
        {value != null ? `${value}${unit}` : "—"}
      </span>
      <span>{label}</span>
    </span>
  );
}

function TrendChartsSection({ trends }: { trends: ReportTrend[] }) {
  const bp = trends.find((t) => t.metric === "blood_pressure");
  const bg = trends.find((t) => t.metric === "blood_glucose");
  const wt = trends.find((t) => t.metric === "weight");

  const charts: { key: string; label: string; trend: ReportTrend | undefined }[] = [
    { key: "bp", label: "혈압", trend: bp },
    { key: "bg", label: "혈당", trend: bg },
    { key: "wt", label: "체중", trend: wt },
  ];

  return (
    <SectionCard title="건강지표 추이">
      <div className="space-y-6">
        {charts.map(({ key, label, trend }) => {
          const series = toStatSeries(trend);
          const meta =
            TREND_METRIC_META[trend?.metric ?? "blood_pressure"];
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-text-primary">{label}</p>
                <div className="flex gap-2 flex-wrap justify-end">
                  {trend && key === "bp" && (
                    <>
                      <TrendSummaryBadge
                        label="평균 수축기"
                        value={trend.avg}
                        unit={meta.unit}
                      />
                      <TrendSummaryBadge
                        label="평균 이완기"
                        value={trend.secondary_avg}
                        unit={meta.unit}
                      />
                    </>
                  )}
                  {trend && key !== "bp" && (
                    <TrendSummaryBadge
                      label="평균"
                      value={trend.avg}
                      unit={meta.unit}
                    />
                  )}
                </div>
              </div>
              {series.length === 0 ? (
                <div className="flex items-center justify-center h-16 bg-surface rounded-[10px]">
                  <p className="text-sm text-text-tertiary">데이터 없음</p>
                </div>
              ) : key === "bp" ? (
                <BPTrendChart series={series} />
              ) : key === "bg" ? (
                <BGTrendChart series={series} />
              ) : (
                <WeightTrendChart series={series} />
              )}
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}

/* ── 6. 챌린지 수행 내역 ─── */

const CHALLENGE_CATEGORIES = [
  { key: "ALL", label: "전체" },
  { key: "EXERCISE", label: "운동" },
  { key: "DIET", label: "식단" },
  { key: "SLEEP", label: "수면" },
  { key: "WATER", label: "수분" },
  { key: "NO_SMOKING", label: "금연" },
  { key: "NO_ALCOHOL", label: "금주" },
  { key: "DISEASE_CARE", label: "질환관리" },
  { key: "MEDITATION", label: "명상" },
];

function ChallengeListSection({ challenges }: { challenges: ReportChallenge[] }) {
  const [filter, setFilter] = useState<string>("ALL");

  const presentCategories = new Set(challenges.map((c) => c.category));
  const visibleTabs = CHALLENGE_CATEGORIES.filter(
    (t) => t.key === "ALL" || presentCategories.has(t.key)
  );

  const effectiveFilter = visibleTabs.some((t) => t.key === filter) ? filter : "ALL";

  const filtered =
    effectiveFilter === "ALL"
      ? challenges
      : challenges.filter((c) => c.category === effectiveFilter);

  return (
    <SectionCard title="챌린지 수행 내역">
      {challenges.length === 0 ? (
        <p className="text-sm text-text-tertiary text-center py-6">
          이번 달 챌린지 참여 내역이 없습니다.
        </p>
      ) : (
        <>
          {/* 카테고리 필터 */}
          <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
            {visibleTabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setFilter(tab.key)}
                className={[
                  "shrink-0 px-3 py-1 rounded-full text-xs font-semibold transition-colors",
                  effectiveFilter === tab.key
                    ? "bg-brand-black text-white"
                    : "bg-surface text-text-secondary hover:bg-border",
                ].join(" ")}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* 챌린지 목록 */}
          <div className="space-y-3">
            {filtered.map((c) => {
              const statusStyle =
                CHALLENGE_STATUS_STYLE[c.status] ?? CHALLENGE_STATUS_STYLE.in_progress;
              return (
                <div key={c.challenge_id} className="flex items-start gap-3">
                  <span className="text-xl shrink-0 mt-0.5" aria-hidden="true">
                    {CATEGORY_EMOJI[c.category] ?? "💪"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {c.title}
                      </p>
                      <span
                        className={[
                          "shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full",
                          statusStyle.bg,
                          statusStyle.text,
                        ].join(" ")}
                      >
                        {statusStyle.label}
                      </span>
                    </div>
                    {/* 진행 바 */}
                    <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-black rounded-full transition-all duration-500"
                        style={{ width: `${c.progress_percent}%` }}
                      />
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-xs text-text-tertiary">
                        {c.success_days}/{c.goal_days}일
                      </span>
                      <span className="text-xs font-bold text-text-secondary">
                        {c.progress_percent}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </SectionCard>
  );
}

/* ── 7. 사용자가 지킨 좋은 습관 ─── */

function GoodHabitsSection({ habits }: { habits: ReportGoodHabit[] }) {
  if (habits.length === 0) return null;

  return (
    <SectionCard title="이번 달 잘 지킨 습관">
      <div className="space-y-2">
        {habits.map((h) => (
          <div
            key={h.key}
            className="flex items-start gap-3 bg-green-50 rounded-[12px] px-4 py-3"
          >
            <span className="text-green-600 font-bold text-sm shrink-0">✓</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-green-800">{h.label}</p>
              {h.evidence && (
                <p className="text-xs text-green-700 mt-0.5">{h.evidence}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

/* ── 8. disclaimer ─── */

function Disclaimer() {
  return (
    <div className="bg-surface rounded-[12px] px-4 py-3">
      <p className="text-xs text-text-tertiary leading-relaxed">
        이 리포트는 기록된 건강 데이터를 바탕으로 작성된 참고 자료입니다. 의료적
        진단이나 처방을 대체하지 않으며, 건강 이상이 의심될 경우 반드시 의료진과
        상담하시기 바랍니다.
      </p>
    </div>
  );
}

/* ── 공통 섹션 카드 래퍼 ─── */

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
      <h3 className="font-bold text-text-primary mb-4">{title}</h3>
      {children}
    </div>
  );
}

/* =========================================================
   메인 컴포넌트
   ========================================================= */

export default function ReportTab() {
  const [mode, setMode] = useState<ReportMode>("monthly");
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  // 임의 기간 기본값: 최근 30일
  const [rangeFrom, setRangeFrom] = useState<string>(
    format(subDays(new Date(), 29), "yyyy-MM-dd"),
  );
  const [rangeTo, setRangeTo] = useState<string>(format(new Date(), "yyyy-MM-dd"));
  const { showToast } = useToast();

  const monthStr = format(currentMonth, "yyyy-MM");
  const rangeValid = !!rangeFrom && !!rangeTo && rangeFrom <= rangeTo;

  // 두 훅 모두 호출하되 활성 모드만 enabled (hooks 규칙: 조건부 호출 불가).
  const monthlyQuery = useMonthlyReportV2(monthStr, mode === "monthly");
  const rangeQuery = useMonthlyReportV2Range(
    rangeFrom,
    rangeTo,
    mode === "custom" && rangeValid,
  );
  const { data: report, isLoading } =
    mode === "monthly" ? monthlyQuery : rangeQuery;

  const hasReport = !!report && !isLoading;

  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const handlePdfDownload = async () => {
    if (isPdfLoading) return;
    setIsPdfLoading(true);
    let objectUrl: string | undefined;
    try {
      const { blob, filename } = await requestMonthlyReportPdf(
        mode === "monthly"
          ? { period: "monthly", month: monthStr }
          : { period: "custom", dateFrom: rangeFrom, dateTo: rangeTo },
      );
      objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      showToast("PDF 생성에 실패했어요. 잠시 후 다시 시도해 주세요.", "error");
    } finally {
      // click/remove 에서 예외가 나도 objectUrl 누수가 없도록 finally 에서 해제.
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setIsPdfLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 헤더 영역: 조회 모드 토글 + (월 네비게이션 | 기간 선택) */}
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <div className="mb-3">
          <ModeToggle mode={mode} onChange={setMode} />
        </div>
        <div className="flex items-center justify-between mb-4">
          {mode === "monthly" ? (
            <MonthNav
              current={currentMonth}
              onPrev={() => setCurrentMonth((d) => subMonths(d, 1))}
              onNext={() => setCurrentMonth((d) => addMonths(d, 1))}
            />
          ) : (
            <RangePicker
              from={rangeFrom}
              to={rangeTo}
              onFrom={setRangeFrom}
              onTo={setRangeTo}
            />
          )}
          {/* PDF 버튼 — 서버 렌더(format=pdf) 요청 후 새 탭으로 열기 */}
          <button
            type="button"
            onClick={handlePdfDownload}
            disabled={!hasReport || isPdfLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-[8px] bg-surface text-text-primary transition-colors hover:bg-border disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="PDF로 저장"
            aria-busy={isPdfLoading}
          >
            <span aria-hidden="true">📄</span>
            {isPdfLoading ? "생성 중…" : "PDF 저장"}
          </button>
        </div>

        {/* 헤더 통계 */}
        {hasReport && report.header_stats && <HeaderStatsRow stats={report.header_stats} />}
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="animate-pulse space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-40 bg-surface rounded-[16px]" />
          ))}
        </div>
      )}

      {/* 잘못된 기간 안내 (custom 모드) */}
      {mode === "custom" && !rangeValid && (
        <div className="text-center py-16 space-y-2">
          <p className="text-4xl" aria-hidden="true">📅</p>
          <p className="font-semibold text-text-primary">조회 기간을 확인해 주세요</p>
          <p className="text-sm text-text-secondary">
            시작일은 종료일보다 이후일 수 없어요.
          </p>
        </div>
      )}

      {/* 데이터 없음 */}
      {(mode === "monthly" || rangeValid) && !isLoading && !hasReport && (
        <div className="text-center py-16 space-y-2">
          <p className="text-4xl" aria-hidden="true">📭</p>
          <p className="font-semibold text-text-primary">
            {mode === "monthly" ? "해당 월 리포트가 없습니다" : "해당 기간 리포트가 없습니다"}
          </p>
          <p className="text-sm text-text-secondary">
            건강 데이터를 기록하면 리포트를 확인할 수 있어요.
          </p>
        </div>
      )}

      {/* 리포트 본문 */}
      {hasReport && (
        <>
          {/* 2. 위험도 예측 결과 */}
          <DiseaseRiskSection risks={report.disease_risks} />

          {/* 3. 판단 근거 TOP 5 */}
          <TopFactorsSection risks={report.disease_risks} />

          {/* 4. 건강지표 추이 */}
          <TrendChartsSection trends={report.trends} />

          {/* 5. 챌린지 수행 내역 */}
          <ChallengeListSection challenges={report.challenges} />

          {/* 6. 좋은 습관 */}
          <GoodHabitsSection habits={report.good_habits} />

          {/* 7. disclaimer */}
          <Disclaimer />
        </>
      )}
    </div>
  );
}
