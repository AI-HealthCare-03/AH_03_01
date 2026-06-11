"use client";

import { useState } from "react";
import { format, addMonths, subMonths } from "date-fns";
import { ko } from "date-fns/locale";
import { useMonthlyReport } from "@/hooks/queries/useMonthlyReport";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { useToast } from "@/components/ui/Toast";
import RiskDonut from "@/components/home/RiskDonut";
import type { RiskGrade } from "@/types/api";
import type { ContributingFactor } from "@/types/health";

/* ── 월 이동 ─────────────────────────── */

interface MonthNavProps {
  current: Date;
  onPrev: () => void;
  onNext: () => void;
}

function MonthNav({ current, onPrev, onNext }: MonthNavProps) {
  const isCurrentMonth =
    format(current, "yyyy-MM") === format(new Date(), "yyyy-MM");
  return (
    <div className="flex items-center gap-4">
      <button
        type="button"
        onClick={onPrev}
        className="p-2 rounded-[8px] hover:bg-surface transition-colors"
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
        className="p-2 rounded-[8px] hover:bg-surface transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="다음 달"
      >
        ▶
      </button>
    </div>
  );
}

/* ── 기여 인자 TOP 3 ─────────────────── */

function ContributingTop3({ factors }: { factors: ContributingFactor[] }) {
  const top3 = [...factors].sort((a, b) => b.weight - a.weight).slice(0, 3);

  return (
    <div className="space-y-2">
      {top3.map((f, i) => (
        <div key={f.factor} className="flex items-center gap-3">
          <span className="w-6 h-6 rounded-full bg-brand text-brand-black text-xs font-bold flex items-center justify-center shrink-0">
            {i + 1}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary truncate">
              {f.factor}
            </p>
            {f.description && (
              <p className="text-xs text-text-secondary">{f.description}</p>
            )}
          </div>
          <span className="text-xs font-bold text-text-secondary shrink-0">
            +{(f.weight * 100).toFixed(0)}
          </span>
        </div>
      ))}
      {factors.length === 0 && (
        <p className="text-sm text-text-tertiary">
          이번 달 위험 인자 데이터가 없습니다.
        </p>
      )}
    </div>
  );
}

/* ── 챌린지 수행 내역 ────────────────── */

interface ChallengeSummaryCardProps {
  summary?: {
    participated?: number;
    succeeded?: number;
    failed?: number;
    in_progress?: number;
    items?: {
      id: number;
      title: string;
      category: string;
      progress_rate: number;
      status: string;
    }[];
  };
}

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

function ChallengeSummaryCard({ summary }: ChallengeSummaryCardProps) {
  if (!summary || Object.keys(summary).length === 0) {
    return (
      <p className="text-sm text-text-tertiary py-4 text-center">
        이번 달 챌린지 참여 내역이 없습니다.
      </p>
    );
  }

  const counts = [
    {
      label: "참여",
      value: summary.participated ?? 0,
      color: "text-status-info",
    },
    {
      label: "성공",
      value: summary.succeeded ?? 0,
      color: "text-status-success",
    },
    { label: "실패", value: summary.failed ?? 0, color: "text-status-danger" },
    {
      label: "진행중",
      value: summary.in_progress ?? 0,
      color: "text-[#856404]",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        {counts.map((c) => (
          <div key={c.label} className="flex flex-col items-center gap-0.5">
            <span className={`text-xl font-black ${c.color}`}>{c.value}</span>
            <span className="text-xs text-text-tertiary">{c.label}</span>
          </div>
        ))}
      </div>
      {summary.items && summary.items.length > 0 && (
        <div className="space-y-2">
          {summary.items.map((item) => (
            <div key={item.id} className="flex items-center gap-3">
              <span className="text-lg" aria-hidden="true">
                {CATEGORY_EMOJI[item.category] ?? "💪"}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {item.title}
                </p>
                <div className="mt-1 h-1.5 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-black rounded-full"
                    style={{ width: `${item.progress_rate}%` }}
                  />
                </div>
              </div>
              <span className="text-xs font-bold text-text-secondary shrink-0">
                {item.progress_rate}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── 메인 컴포넌트 ─────────────────── */

export default function ReportTab() {
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const { showToast } = useToast();

  const monthStr = format(currentMonth, "yyyy-MM");
  const { data: report, isLoading } = useMonthlyReport(monthStr);

  /* 예측 데이터: RiskDonut 에 필요 */
  const { data: predictions } = useLatestPredictions();
  const predItems = predictions?.items ?? [];

  /* 백엔드는 disease_risk_summary: { HYPERTENSION: {risk_score, risk_level}, ... } 형식.
     UI 가 기대하는 평탄한 객체로 정규화. */
  const summary = report?.disease_risk_summary ?? {};
  const summaryFor = (key: string) => {
    const entry = summary[key];
    if (!entry) return null;
    return {
      score: Number(entry.risk_score) || 0,
      level: entry.risk_level,
    };
  };
  /* TOP 3 위험 인자는 백엔드 리포트 응답에 없으므로 latest hypertension prediction 의
     contributing_factors 에서 가져옴. PredictionItem 타입에 contributing_factors 가
     정의되어 있지 않아 백엔드 실제 응답에 맞게 캐스팅. (다음 라운드: 타입 정합성 정리) */
  type PredictionWithFactors = (typeof predItems)[number] & {
    contributing_factors?: ContributingFactor[];
  };
  const dominant = (predItems as PredictionWithFactors[])
    .slice()
    .sort((a, b) => Number(b.risk_score) - Number(a.risk_score))[0];
  const top3Factors: ContributingFactor[] = (
    dominant?.contributing_factors ?? []
  )
    .slice()
    .sort(
      (a: ContributingFactor, b: ContributingFactor) =>
        (b.weight ?? 0) - (a.weight ?? 0),
    )
    .slice(0, 3);
  const challengeSummary = report?.challenge_summary;

  const hyp = summaryFor("HYPERTENSION");
  const dia = summaryFor("DIABETES");
  const car = summaryFor("CARDIOVASCULAR");

  /* 도넛 데이터 */
  const donutData = [
    {
      label: "고혈압",
      disease: "HYPERTENSION",
      score: hyp?.score ?? 0,
      grade: hyp?.level as RiskGrade | undefined,
      factorCount:
        predItems.find((p) => p.disease_type === "HYPERTENSION")
          ?.risk_factors_count ?? 0,
    },
    {
      label: "당뇨",
      disease: "DIABETES",
      score: dia?.score ?? 0,
      grade: dia?.level as RiskGrade | undefined,
      factorCount:
        predItems.find((p) => p.disease_type === "DIABETES")
          ?.risk_factors_count ?? 0,
    },
    {
      label: "심혈관",
      disease: "CARDIOVASCULAR",
      score: car?.score ?? 0,
      grade: car?.level as RiskGrade | undefined,
      factorCount:
        predItems.find((p) => p.disease_type === "CARDIOVASCULAR")
          ?.risk_factors_count ?? 0,
    },
  ];

  const handleActionToast = () => {
    showToast("준비 중인 기능입니다.", "info");
  };

  return (
    <div className="space-y-5">
      {/* 월 이동 */}
      <MonthNav
        current={currentMonth}
        onPrev={() => setCurrentMonth((d) => subMonths(d, 1))}
        onNext={() => setCurrentMonth((d) => addMonths(d, 1))}
      />

      {isLoading ? (
        <div className="animate-pulse space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-40 bg-surface rounded-[16px]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 카드 1: 이번 달 위험도 */}
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
            <h3 className="font-bold text-text-primary mb-4">이번 달 위험도</h3>
            {hyp || dia || car ? (
              <div className="flex justify-around">
                {donutData.map((d) => (
                  <RiskDonut
                    key={d.disease}
                    score={d.score}
                    grade={(d.grade ?? "NORMAL") as RiskGrade}
                    label={d.label}
                    riskFactorCount={d.factorCount}
                    size={80}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-tertiary text-center py-4">
                이번 달 위험도 데이터가 없습니다.
              </p>
            )}
          </div>

          {/* 카드 2: 판단 근거 TOP 3 */}
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
            <h3 className="font-bold text-text-primary mb-4">
              주요 위험 인자 TOP 3
            </h3>
            <ContributingTop3 factors={top3Factors} />
          </div>

          {/* 카드 3: 챌린지 수행 내역 */}
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] md:col-span-2">
            <h3 className="font-bold text-text-primary mb-4">
              챌린지 수행 내역
            </h3>
            <ChallengeSummaryCard summary={challengeSummary} />
          </div>

          {/* 카드 4: 코칭 한 마디 */}
          <div className="bg-brand-yellow-light rounded-[16px] p-5 md:col-span-2">
            <p className="text-xs font-semibold text-[#856404] mb-1">
              💡 코칭 한 마디
            </p>
            <p className="text-sm text-text-primary">
              {report?.coaching_message ??
                "꾸준한 기록이 건강 관리의 첫걸음입니다. 오늘도 혈압과 혈당을 체크해 보세요!"}
            </p>
          </div>
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="flex gap-2 flex-wrap">
        {["미리보기", "PDF로 저장", "의료진 공유"].map((label) => (
          <button
            key={label}
            type="button"
            onClick={handleActionToast}
            className="px-4 py-2 text-sm font-medium border border-border rounded-[10px] bg-white hover:bg-surface transition-colors"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
