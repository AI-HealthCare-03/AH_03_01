"use client";

import { useState } from "react";
import Link from "next/link";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { usePredictionsList } from "@/hooks/queries/usePredictionsList";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import { useRiskRecommendation } from "@/hooks/queries/useRiskRecommendation";
import RiskDonut from "@/components/home/RiskDonut";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type { RiskGrade, DiseaseType, ChallengeCategory } from "@/types/api";
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

  const maxWeight = Math.max(...factors.map((f) => Math.abs(f.weight)), 1);

  return (
    <div className="space-y-3">
      {factors.map((f) => {
        const pct = Math.min(Math.round((Math.abs(f.weight) / maxWeight) * 100), 100);
        const label = f.description
          ? f.description.replace(/\s*(위험\s*(증가|감소)[↑↓]?)?\s*$/, "").trim()
          : f.factor;
        const isRisk = f.weight > 0;
        const direction = isRisk ? "위험 증가↑" : "위험 감소↓";
        // 위험 증가 → 빨간 막대 / 위험 감소 → 파란 막대
        const barColor = isRisk ? "bg-status-danger" : "bg-blue-400";

        return (
          <div key={f.factor}>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-text-primary font-medium">{label}</span>
              <span className="text-xs font-bold text-text-secondary">{pct}점</span>
            </div>
            <div className="h-2 bg-surface rounded-full overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full transition-all duration-500`}
                style={{ width: `${pct}%` }}
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${label} 기여도`}
              />
            </div>
            <p className="text-xs text-text-tertiary mt-0.5">{direction}</p>
          </div>
        );
      })}
    </div>
  );
}

/* ── 한눈에 보는 요약 카드 ─────────── */

interface SummaryCardsProps {
  highestDiseaseLabel: string;
  highestGrade: RiskGrade;
  topFactor: string | null;
  challengeGoal: string | null;
}

const GRADE_COLOR: Record<RiskGrade, string> = {
  NORMAL: "text-status-success",
  CAUTION: "text-status-warning",
  RISK: "text-status-danger",
  DANGER: "text-status-danger",
  HIGH_RISK: "text-status-danger",
  HIGH_DANGER: "text-status-danger",
};

const GRADE_LABEL: Record<RiskGrade, string> = {
  NORMAL: "정상", CAUTION: "주의", RISK: "위험",
  DANGER: "위험", HIGH_RISK: "고위험", HIGH_DANGER: "고위험",
};

function SummaryCards({ highestDiseaseLabel, highestGrade, topFactor, challengeGoal }: SummaryCardsProps) {
  const cards = [
    {
      icon: "🎯",
      title: "가장 우선 관리",
      value: highestDiseaseLabel || "—",
      sub: GRADE_LABEL[highestGrade],
      subColor: GRADE_COLOR[highestGrade],
    },
    {
      icon: "⚠️",
      title: "가장 큰 영향 요인",
      value: topFactor || "—",
      sub: topFactor ? "위험 기여 1위" : "데이터 입력 필요",
      subColor: "text-text-tertiary",
    },
    {
      icon: "🏃",
      title: "이번 주 추천 목표",
      value: challengeGoal || "챌린지 참여하기",
      sub: "건강 개선 시작",
      subColor: "text-text-tertiary",
    },
    {
      icon: "📊",
      title: "정확도 향상",
      value: "추가 데이터 입력",
      sub: "허리둘레·수면 등 입력 시 향상",
      subColor: "text-text-tertiary",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.title}
          className="bg-white rounded-[14px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.08)]"
        >
          <p className="text-xl mb-2">{card.icon}</p>
          <p className="text-[11px] text-text-tertiary font-medium mb-1">{card.title}</p>
          <p className="text-sm font-bold text-text-primary leading-snug">{card.value}</p>
          <p className={`text-[11px] mt-0.5 font-medium ${card.subColor}`}>{card.sub}</p>
        </div>
      ))}
    </div>
  );
}

/* ── AI 맞춤 제안 ───────────────────── */

function AiSuggestions({ predictionId }: { predictionId: number | undefined }) {
  const { data: recData, isLoading: recLoading } = useRiskRecommendation(predictionId);
  const { data: challengeData, isLoading: challengeLoading } = useChallengeRecommendations(predictionId, 3);

  const recommendations = recData?.recommendations ?? [];
  const challenges = challengeData?.items ?? [];

  /* 카테고리별 권고사항 분류 */
  const exerciseRec = recommendations.find((r) => r.category === "EXERCISE");
  const dietRec = recommendations.find((r) => r.category === "DIET");
  const generalRecs = recommendations.filter(
    (r) => r.category !== "EXERCISE" && r.category !== "DIET"
  ).slice(0, 3);
  const displayRecs = generalRecs.length > 0 ? generalRecs : recommendations.slice(0, 3);

  /* 식단 추천 — DIET 권고사항 or 기본 문구 */
  const dietItems = dietRec
    ? [dietRec.content]
    : ["채소·통곡물 위주 식단을 권장합니다.", "나트륨 섭취를 줄여보세요.", "규칙적인 식사 시간을 유지하세요."];

  if (!predictionId) return null;

  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
      <div className="flex items-center gap-2">
        <span className="text-lg">✨</span>
        <h3 className="font-bold text-text-primary">AI 맞춤 제안</h3>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {/* 권고사항 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span>💡</span> 권고사항
          </p>
          {recLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-surface rounded-[8px]" />)}
            </div>
          ) : displayRecs.length > 0 ? (
            <ul className="space-y-2">
              {displayRecs.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                  <span className="text-status-success mt-0.5 shrink-0">✓</span>
                  <span>{rec.content}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Link
              href={`/predictions/${predictionId}/recommendations`}
              className="block text-xs text-brand-black font-semibold underline"
            >
              자세히 보기 →
            </Link>
          )}
          {displayRecs.length > 0 && (
            <Link
              href={`/predictions/${predictionId}/recommendations`}
              className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
            >
              자세히 보기 →
            </Link>
          )}
        </div>

        {/* 추천 챌린지 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span>🏆</span> 추천 챌린지
          </p>
          {challengeLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-surface rounded-[8px]" />)}
            </div>
          ) : challenges.length > 0 ? (
            <ul className="space-y-2">
              {challenges.map((item, idx) => (
                <li
                  key={item.template_id ?? item.challenge_id ?? idx}
                  className="flex items-center gap-2 p-2 bg-surface rounded-[8px]"
                >
                  <span className="text-base shrink-0">
                    {CATEGORY_CONFIG[item.category as ChallengeCategory]?.emoji ?? "💪"}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-text-primary truncate">
                      {item.title && item.title !== item.category
                        ? item.title
                        : (CATEGORY_CONFIG[item.category as ChallengeCategory]?.label ?? item.category)}
                    </p>
                    <p className="text-[10px] text-brand-black font-bold">+{item.reward_points ?? 200}P</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-tertiary">추천 챌린지가 없습니다.</p>
          )}
        </div>

        {/* 식단 추천 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span>🥗</span> 식단 추천
          </p>
          {exerciseRec && (
            <div className="p-2 bg-surface rounded-[8px] mb-2">
              <p className="text-[11px] text-text-secondary">{exerciseRec.content}</p>
            </div>
          )}
          <ul className="space-y-2">
            {dietItems.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="text-brand-black mt-0.5 shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 면책 */}
      <p className="text-[10px] text-text-tertiary border-t border-border pt-3">
        본 권고사항은 입력하신 건강 데이터를 바탕으로 제공되는 일반적인 건강 정보로,
        의료적 진단이나 처방을 대체하지 않습니다. 정확한 진단과 치료는 반드시 의료 전문가에게 문의하세요.
      </p>
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
                <div className="flex items-center gap-1 mb-0.5">
                  <span className="text-sm">
                    {CATEGORY_CONFIG[item.category as ChallengeCategory]?.emoji ?? "💪"}
                  </span>
                  <p className="text-xs font-semibold text-text-primary">
                    {item.title && item.title !== item.category
                      ? item.title
                      : (CATEGORY_CONFIG[item.category as ChallengeCategory]?.label ?? item.category)}
                  </p>
                </div>
                {item.reason && !item.reason.includes("위험도") && (
                  <p className="text-[11px] text-text-tertiary">{item.reason}</p>
                )}
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
      score: Math.round(Number(lite?.risk_score ?? detail?.risk_score ?? 0)),
      grade: riskLevelToGrade(detail?.risk_level) ?? (lite?.risk_grade ?? "NORMAL"),
      factorCount: detail?.contributing_factors?.length ?? 0,
      predId: lite?.id ?? detail?.id,
    };
  });

  /* 현재 선택된 disease 의 상세 */
  const selectedDetail = detailItems.find((p) => p.disease_type === activeDisease);
  const selectedLite = latestItems.find((p) => p.disease_type === activeDisease);
  const selectedPredId = selectedLite?.id;

  /* 종합 등급 헤드라인 — 가장 높은 위험 */
  const gradeOrder: RiskGrade[] = ["HIGH_RISK", "HIGH_DANGER", "RISK", "DANGER", "CAUTION", "NORMAL"];
  const highestGrade =
    donutData
      .map((d) => d.grade)
      .sort((a, b) => gradeOrder.indexOf(a) - gradeOrder.indexOf(b))[0] ?? "NORMAL";

  const highestDiseaseData = donutData
    .filter((d) => d.grade === highestGrade)
    .sort((a, b) => b.score - a.score)[0];

  const highestDiseaseLabel =
    donutData
      .filter((d) => d.grade === highestGrade)
      .map((d) => DISEASE_LABELS[d.disease])
      .join(", ");

  /* 가장 큰 영향 요인 — 최고 위험 질환의 top1 기여 인자 */
  const highestDetail = detailItems.find(
    (p) => p.disease_type === highestDiseaseData?.disease
  );
  const topFactor = highestDetail?.contributing_factors?.[0]
    ? (() => {
        const f = highestDetail.contributing_factors[0];
        return f.description
          ? f.description.replace(/\s*(위험\s*(증가|감소)[↑↓]?)?\s*$/, "").trim()
          : f.factor;
      })()
    : null;

  /* AI 맞춤 제안용 — 최고 위험 질환 예측 ID */
  const highestPredId = highestDiseaseData?.predId;

  /* 추천 챌린지 첫 번째 — 요약 카드용 */
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
              {highestDiseaseLabel}{" "}
              <span className="text-status-danger">{GRADE_LABEL[highestGrade]}</span>
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

      {/* 한눈에 보는 요약 카드 */}
      <SummaryCards
        highestDiseaseLabel={highestDiseaseLabel}
        highestGrade={highestGrade}
        topFactor={topFactor}
        challengeGoal={null}
      />

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

      {/* AI 맞춤 제안 */}
      <AiSuggestions predictionId={highestPredId} />

      {/* 면책 */}
      <Disclaimer />
    </div>
  );
}
