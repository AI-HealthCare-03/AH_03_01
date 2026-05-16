"use client";

import type { ChallengeCategory } from "@/types/challenge";

/* =========================================
   카테고리별 이모지 + 한글 라벨 매핑
   이 컴포넌트 한 곳에서만 관리
   ========================================= */

export const CATEGORY_CONFIG: Record<
  ChallengeCategory,
  { emoji: string; label: string; color: string }
> = {
  EXERCISE: { emoji: "🏃", label: "운동", color: "bg-orange-50 text-orange-600" },
  WATER: { emoji: "💧", label: "물 마시기", color: "bg-blue-50 text-blue-600" },
  SLEEP: { emoji: "😴", label: "수면", color: "bg-indigo-50 text-indigo-600" },
  DIET: { emoji: "🥗", label: "식습관", color: "bg-green-50 text-green-600" },
  NO_SMOKING: { emoji: "🚭", label: "금연", color: "bg-red-50 text-red-600" },
  NO_ALCOHOL: { emoji: "🚫", label: "금주", color: "bg-purple-50 text-purple-600" },
  DISEASE_CARE: { emoji: "💊", label: "질환 관리", color: "bg-teal-50 text-teal-600" },
  MEDITATION: { emoji: "🧘", label: "명상", color: "bg-yellow-50 text-yellow-600" },
};

interface ChallengeCategoryIconProps {
  category: ChallengeCategory;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const sizeClasses = {
  sm: "w-8 h-8 text-base",
  md: "w-10 h-10 text-xl",
  lg: "w-14 h-14 text-3xl",
};

export default function ChallengeCategoryIcon({
  category,
  size = "md",
  showLabel = false,
}: ChallengeCategoryIconProps) {
  const config = CATEGORY_CONFIG[category] ?? CATEGORY_CONFIG.EXERCISE;

  return (
    <span className="inline-flex flex-col items-center gap-1">
      <span
        className={[
          "flex items-center justify-center rounded-full",
          config.color,
          sizeClasses[size],
        ].join(" ")}
        aria-label={config.label}
      >
        {config.emoji}
      </span>
      {showLabel && (
        <span className="text-xs text-text-secondary font-medium">
          {config.label}
        </span>
      )}
    </span>
  );
}
