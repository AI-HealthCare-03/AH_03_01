"use client";

import { useState } from "react";
import Link from "next/link";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { usePredictionsList } from "@/hooks/queries/usePredictionsList";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import RiskDonut from "@/components/home/RiskDonut";
import type { RiskGrade, DiseaseType } from "@/types/api";
import type { PredictionDetail } from "@/types/health";

/* ── 상수 ──────────────────────────── */

const DISEASE_LABELS: Record<DiseaseType, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
};

const DISEASE_TABS: { id: DiseaseType; label: string }[] = [
  { id: "HYPERTENSION", label: "고혈압" },
  { id: "DIABETES", label: "당뇨" },
  { id: "CARDIOVASCULAR", label: "심혈관" },
];

/* ── RiskLevel 매핑 ─────────────────── */

function riskLevelToGrade(level?: string): RiskGrade {
  switch (level) {
    case "NORMAL": return "NORMAL";
    case "CAUTION": return "CAUTION";
    case "RISK": return "DANGER";
    case "HIGH_RISK": return "HIGH_DANGER";
    default: return "NORMAL";
  }
}

/* ── 기여 인자 바 ───────────────────── */

interface ContributingBarsProps {
  factors: { factor: string; weight: number; description?: string }[];
}

function ContributingBars({ factors }: ContributingBarsProps) {
  if (factors.length === 0) {
    return (
      <div className="py-6 text-center space-y-1">
        <p className="text-sm text-text-tertiary">분석된 위험 인자가 없습니다.</p>
        <Link href="/health-records/new" className="text-sm font-semibold text-text-primary underline">
          데이터 입력하기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {factors.map((f) => {
        const pct = Math.min(Math.round(f.weight * 100), 100);
        return (
          <div key={f.factor}>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-text-primary font-medium">{f.factor}</span>
              <span className="text-xs font-bold text-text-secondary">{pct}점</span>
            </div>
            <div className="h-2 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-black rounded-full transition-all duration-500"
                style={{ width: `${pct}%` }}
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${f.factor} 기여도`}
              />
            </div>
            {f.description && (
              <p className="text-xs text-text-tertiary mt-0.5">{f.description}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── 맞춤 챌린지 추천 사이드 (데스크탑) ── */

function RecommendedChallengesSide({ predictionId }: { predictionId: number | undefined }) {
  const { data, isLoading } = useChallengeRecommendations(predictionId, 3);

  return (
    <div className="hidden md:block w-64 shrink-0">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <h3 className="font-bold text-sm text-text-primary mb-3">맞춤 챌린지 추천</h3>
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-surface rounded-[8px]" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {(data?.items ?? []).map((item, idx) => (
              <div
                key={item.template_id ?? item.challenge_id ?? item.id ?? idx}
                className="flex flex-col gap-0.5 p-3 bg-surface rounded-[10px]"
              >
                <p className="text-xs font-semibold text-text-primary">{item.title}</p>
                <p className="text-[11px] text-text-tertiary">{item.reason}</p>
                <p className="text-[11px] text-brand-black font-bold">
                  +{item.reward_points ?? 200}P
                </p>
              </div>
            ))}
            {(!data || data.items.length === 0) && (
              <p className="text-xs text-text-tertiary">추천 챌린지가 없습니다.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── 면책 ─────────────────────────── */

function Disclaimer() {
  return (
    <div className="rounded-[12px] bg-surface border border-border p-4 text-xs text-text-secondary space-y-1">
      <p className="font-semibold text-text-primary">안내 사항</p>
      <p>
        본 위험도 결과는 의학적 진단이 아닙니다. 정확한 진단·치료는 반드시 의료 전문가에게
        문의하세요.
      </p>
      <p className="text-text-tertiary mt-1">
        출처: KSH 2022 고혈압 진료지침 / KDA 2023 당뇨병 진료지침 /
        KSoLA 2022 이상지질혈증 / KSSO 2022 비만 진료지침
      </p>
    </div>
  );
}

/* ── 메인 컴포넌트 ─────────────────── */

export default function RiskTab() {
  const [activeDisease, setActiveDisease] = useState<DiseaseType>("HYPERTENSION");

  const { data: latestPredictions, isLoading: l1 } = useLatestPredictions();
  const { data: detailPredictions, isLoading: l2 } = usePredictionsList({ latest: true });

  const isLoading = l1 || l2;

  const latestItems = latestPredictions?.items ?? [];
  /* detailPredictions 응답이 PredictionDetailResponse 형식이면 items 배열 */
  const detailItems = (detailPredictions as { items?: PredictionDetail[] } | null)?.items ?? [];

  /* 도넛 데이터 */
  const donutData: {
    disease: DiseaseType;
    score: number;
    grade: RiskGrade;
    factorCount: number;
    predId?: number;
  }[] = DISEASE_TABS.map(({ id }) => {
    const lite = latestItems.find((p) => p.disease_type === id);
    const detail = detailItems.find((p) => p.disease_type === id);
    return {
      disease: id,
      score: lite?.risk_score ?? 0,
      grade: riskLevelToGrade(detail?.risk_level) ?? (lite?.risk_grade ?? "NORMAL"),
      factorCount: lite?.risk_factors_count ?? 0,
      predId: lite?.id,
    };
  });

  /* 현재 선택된 disease 의 상세 */
  const selectedDetail = detailItems.find((p) => p.disease_type === activeDisease);
  const selectedLite = latestItems.find((p) => p.disease_type === activeDisease);
  const selectedPredId = selectedLite?.id;

  /* 종합 등급 헤드라인 — 가장 높은 위험 */
  const gradeOrder: RiskGrade[] = ["HIGH_RISK", "HIGH_DANGER", "RISK", "DANGER", "CAUTION", "NORMAL"];
  const gradeLabel: Record<RiskGrade, string> = {
    HIGH_RISK: "고위험",
    HIGH_DANGER: "고위험",
    RISK: "위험",
    DANGER: "위험",
    CAUTION: "주의",
    NORMAL: "정상",
  };
  const highestGrade =
    donutData
      .map((d) => d.grade)
      .sort((a, b) => gradeOrder.indexOf(a) - gradeOrder.indexOf(b))[0] ?? "NORMAL";

  const highestDiseaseLabel =
    donutData
      .filter((d) => d.grade === highestGrade)
      .map((d) => DISEASE_LABELS[d.disease])
      .join(", ");

  const latestUpdated =
    latestItems[0]?.created_at
      ? new Date(latestItems[0].created_at).toLocaleDateString("ko-KR")
      : null;

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-32 bg-surface rounded-[16px]" />
        <div className="h-64 bg-surface rounded-[16px]" />
      </div>
    );
  }

  /* 빈 상태 */
  if (latestItems.length === 0) {
    return (
      <div className="text-center py-16 space-y-3">
        <p className="text-5xl">🔍</p>
        <p className="font-bold text-text-primary text-lg">위험도 분석이 없습니다</p>
        <p className="text-sm text-text-secondary">
          건강 기록을 입력하면 맞춤 위험도 분석을 받을 수 있어요.
        </p>
        <Link
          href="/health-records/new"
          className="inline-flex items-center gap-1 mt-2 px-5 py-2.5 bg-brand text-brand-black font-semibold rounded-[12px] text-sm hover:bg-brand-hover transition-colors"
        >
          건강 기록 입력하기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* 헤드라인 */}
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-text-tertiary">종합 등급</p>
            <p className="text-xl font-black text-text-primary mt-1">
              {highestDiseaseLabel} <span className="text-status-danger">{gradeLabel[highestGrade]}</span>
            </p>
          </div>
          {latestUpdated && (
            <p className="text-xs text-text-tertiary">갱신: {latestUpdated}</p>
          )}
        </div>
      </div>

      {/* 3 도넛 */}
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <div className="flex justify-around">
          {donutData.map((d) => (
            <RiskDonut
              key={d.disease}
              score={d.score}
              grade={d.grade}
              label={DISEASE_LABELS[d.disease]}
              riskFactorCount={d.factorCount}
              size={96}
            />
          ))}
        </div>
      </div>

      {/* 카테고리 탭 + 기여 인자 */}
      <div className="flex gap-4">
        <div className="flex-1 min-w-0 bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
          {/* 탭 */}
          <div className="flex gap-1 mb-5">
            {DISEASE_TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActiveDisease(id)}
                className={[
                  "flex-1 py-2 text-sm font-medium rounded-[8px] transition-colors border",
                  activeDisease === id
                    ? "bg-brand-black text-white border-brand-black"
                    : "text-text-secondary border-border hover:text-text-primary",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>

          {/* 기여 인자 */}
          <ContributingBars factors={selectedDetail?.contributing_factors ?? []} />

          {/* 권고사항 CTA */}
          {selectedPredId && (
            <Link
              href={`/predictions/${selectedPredId}/recommendations`}
              className="mt-5 w-full flex items-center justify-center gap-2 py-3 bg-brand text-brand-black font-semibold rounded-[12px] text-sm hover:bg-brand-hover transition-colors"
            >
              권고사항 보기 →
            </Link>
          )}
        </div>

        {/* 데스크탑 사이드: 맞춤 챌린지 */}
        <RecommendedChallengesSide predictionId={selectedPredId} />
      </div>

      {/* 면책 */}
      <Disclaimer />
    </div>
  );
}
