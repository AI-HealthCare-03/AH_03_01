"use client";

import ChallengeCategoryIcon, {
  CATEGORY_CONFIG,
} from "@/components/challenges/common/ChallengeCategoryIcon";
import type { ChallengeCategory, ChallengeScope } from "@/types/challenge";

/* =========================================
   Step 2: 카테고리 선택 (8개 4×2 그리드)
   ========================================= */

const ALL_CATEGORIES = Object.keys(CATEGORY_CONFIG) as ChallengeCategory[];

/* 그룹 챌린지에서는 질환 관리(개인 전용) 제외 */
const GROUP_EXCLUDED: ChallengeCategory[] = ["DISEASE_CARE"];

interface WizardStep2Props {
  scope: ChallengeScope;
  value: ChallengeCategory | null;
  onChange: (cat: ChallengeCategory) => void;
}

export default function WizardStep2({ scope, value, onChange }: WizardStep2Props) {
  const categories =
    scope === "GROUP"
      ? ALL_CATEGORIES.filter((c) => !GROUP_EXCLUDED.includes(c))
      : ALL_CATEGORIES;

  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">주제 선택</h2>
      <p className="text-sm text-text-secondary mb-6">
        어떤 생활습관을 개선하고 싶으신가요?
      </p>

      <div className="grid grid-cols-4 gap-3">
        {categories.map((cat) => {
          const isSelected = value === cat;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => onChange(cat)}
              className={[
                "flex flex-col items-center gap-2 p-3 rounded-[14px] border-2 transition-all duration-150",
                isSelected
                  ? "border-brand-black bg-white shadow-sm"
                  : "border-border bg-white hover:border-brand",
              ].join(" ")}
              aria-pressed={isSelected}
              aria-label={CATEGORY_CONFIG[cat].label}
            >
              <ChallengeCategoryIcon category={cat} size="md" />
              <span className="text-[11px] font-medium text-text-secondary text-center leading-tight">
                {CATEGORY_CONFIG[cat].label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
