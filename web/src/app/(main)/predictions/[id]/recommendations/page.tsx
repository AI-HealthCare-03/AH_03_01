"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useRiskRecommendation } from "@/hooks/queries/useRiskRecommendation";
import { usePredictionsList } from "@/hooks/queries/usePredictionsList";
import RecommendationCategoryCard from "@/components/health/recommendations/RecommendationCategoryCard";
import ExerciseDetailModal from "@/components/health/recommendations/ExerciseDetailModal";
import type { RiskGrade } from "@/types/api";
import type { PredictionDetail, RecommendationCategory } from "@/types/health";

/* ── 등급별 헤더 컬러 ─────────────── */

const RISK_HEADER = {
  bg: "bg-[#fff3e0]",
  text: "text-[#e65100]",
  label: "위험",
} as const;
const HIGH_RISK_HEADER = {
  bg: "bg-[#ffeaea]",
  text: "text-status-danger",
  label: "고위험",
} as const;

const GRADE_HEADER: Record<
  RiskGrade,
  { bg: string; text: string; label: string }
> = {
  NORMAL: { bg: "bg-[#e8f5e9]", text: "text-status-success", label: "정상" },
  CAUTION: { bg: "bg-[#fffbe6]", text: "text-[#856404]", label: "주의" },
  RISK: RISK_HEADER,
  HIGH_RISK: HIGH_RISK_HEADER,
  DANGER: RISK_HEADER,
  HIGH_DANGER: HIGH_RISK_HEADER,
};

/* riskLevel → RiskGrade 매핑 */

function levelToGrade(level?: string): RiskGrade {
  switch (level) {
    case "NORMAL":
      return "NORMAL";
    case "CAUTION":
      return "CAUTION";
    case "RISK":
      return "DANGER";
    case "HIGH_RISK":
      return "HIGH_DANGER";
    default:
      return "NORMAL";
  }
}

/* ── 카테고리 설정 ───────────────── */

interface CategoryConfig {
  key: RecommendationCategory;
  icon: string;
  title: string;
  fallback: string;
  isDetailAvailable?: boolean;
}

const CATEGORIES: CategoryConfig[] = [
  {
    key: "EXERCISE",
    icon: "🏃",
    title: "운동",
    fallback:
      "유산소 운동을 주 5일, 1회 30분 이상 실천하세요.\n빠르게 걷기, 자전거 타기, 수영이 혈압·혈당 개선에 효과적입니다.\n\n근력 운동도 주 2~3회 병행하면 인슐린 저항성 개선에 도움이 됩니다.\n\n출처: KSH 2022 고혈압 진료지침 / KDA 2023 당뇨병 진료지침",
    isDetailAvailable: true,
  },
  {
    key: "DIET",
    icon: "🥗",
    title: "식습관",
    fallback:
      "소금 섭취를 하루 6g 미만으로 줄이세요.\n채소·과일·통곡물 중심으로 식단을 구성하고, 포화지방·트랜스지방을 줄이세요.\n\n혈당 관리를 위해 단순당 섭취를 제한하고, 식사를 규칙적으로 하세요.\n과식을 피하고 천천히 씹어 드세요.\n\n출처: KDA 2023 당뇨병 진료지침",
  },
  {
    key: "SMOKING",
    icon: "🚭",
    title: "흡연",
    fallback:
      "흡연은 심혈관 질환 위험을 2~4배 높입니다. 금연을 강력히 권장합니다.\n\n금연보조제(니코틴 패치, 껌) 또는 처방약(바레니클린)이 성공률을 높입니다.\n금연 클리닉 또는 금연 상담 전화(1544-9030)를 이용하세요.\n\n출처: KSH 2022 고혈압 진료지침",
  },
  {
    key: "SLEEP",
    icon: "🌙",
    title: "수면",
    fallback:
      "하루 7~8시간의 규칙적인 수면을 취하세요.\n수면 부족은 혈압 상승과 인슐린 저항성 증가로 이어질 수 있습니다.\n\n취침 1시간 전 스마트폰·TV 사용을 줄이고, 규칙적인 취침·기상 시간을 유지하세요.\n수면 무호흡증이 있다면 전문가 진료를 받으세요.",
  },
];

/* ── 메인 페이지 ─────────────────── */

export default function RecommendationsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const predId = parseInt(id, 10);
  const [exerciseModalOpen, setExerciseModalOpen] = useState(false);

  const { data: rec, isLoading: recLoading } = useRiskRecommendation(predId);
  const { data: predictions, isLoading: predLoading } = usePredictionsList({
    latest: true,
  });

  const isLoading = recLoading || predLoading;

  /* 해당 예측의 등급 */
  const predDetail = (
    predictions as { items?: PredictionDetail[] } | null
  )?.items?.find((p) => p.id === predId);
  const grade = levelToGrade(predDetail?.risk_level);
  const headerConfig = GRADE_HEADER[grade];

  /* 권고사항 카테고리별 매핑 */
  const recMap: Partial<Record<string, string>> = {};
  (rec?.recommendations ?? []).forEach((r) => {
    const cat = r.category?.toUpperCase();
    recMap[cat] = recMap[cat] ? `${recMap[cat]}\n\n${r.content}` : r.content;
  });

  const disclaimer =
    rec?.disclaimer ??
    "본 권고사항은 의학적 진단이 아닙니다. 개인 상태에 따라 다를 수 있으므로, 정확한 진단·치료는 반드시 의료 전문가에게 문의하세요.";

  return (
    <div className="max-w-3xl mx-auto">
      {/* 뒤로 */}
      <div className="px-4 pt-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm text-text-secondary hover:text-text-primary flex items-center gap-1 mb-4"
        >
          ← 뒤로
        </button>
      </div>

      {/* 등급별 컬러 헤더 */}
      <div className={`px-4 py-5 ${headerConfig.bg}`}>
        <div className="flex items-center gap-2 mb-1">
          <p className={`text-xs font-semibold ${headerConfig.text}`}>
            {headerConfig.label} 등급 맞춤 권고사항
          </p>
          {predDetail?.risk_level_label && (
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-white/70 text-text-primary border border-white/50">
              {predDetail.risk_level_label}
            </span>
          )}
        </div>
        <h1 className="text-xl font-black text-text-primary">
          생활습관 개선 권고사항
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          아래 항목을 꾸준히 실천하면 위험도를 낮출 수 있습니다.
        </p>
      </div>

      {/* 콘텐츠 */}
      <div className="px-4 py-5 space-y-3">
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-surface rounded-[16px]" />
            ))}
          </div>
        ) : (
          CATEGORIES.map((cat) => (
            <RecommendationCategoryCard
              key={cat.key}
              icon={cat.icon}
              title={cat.title}
              content={recMap[cat.key] ?? cat.fallback}
              isDetailAvailable={cat.isDetailAvailable}
              onDetailClick={
                cat.key === "EXERCISE"
                  ? () => setExerciseModalOpen(true)
                  : undefined
              }
            />
          ))
        )}

        {/* 면책 */}
        <div className="rounded-[12px] bg-surface border border-border p-4 text-xs text-text-secondary">
          <p className="font-semibold text-text-primary mb-1">안내 사항</p>
          <p>{disclaimer}</p>
          <p className="text-text-tertiary mt-2">
            출처: KSH 2022 / KDA 2023 / KSoLA 2022 / KSSO 2022
          </p>
        </div>

        {/* CTA */}
        <Link
          href="/challenges/new?category=NO_SMOKING"
          className="flex items-center justify-center gap-2 w-full py-4 bg-brand text-brand-black font-bold rounded-[14px] text-sm hover:bg-brand-hover transition-colors"
        >
          맞춤 챌린지 시작하기 →
        </Link>
      </div>

      {/* 운동 자세히 모달 */}
      <ExerciseDetailModal
        open={exerciseModalOpen}
        onClose={() => setExerciseModalOpen(false)}
      />
    </div>
  );
}
