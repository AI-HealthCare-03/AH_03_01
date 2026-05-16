"use client";

import type { ExerciseSubType } from "@/types/challenge";

/* =========================================
   Step 3: 운동 종류 선택 (EXERCISE 카테고리 전용)
   ========================================= */

const EXERCISE_OPTIONS: {
  value: ExerciseSubType;
  emoji: string;
  label: string;
}[] = [
  { value: "WALKING", emoji: "🚶", label: "걷기" },
  { value: "RUNNING", emoji: "🏃", label: "러닝" },
  { value: "STRENGTH", emoji: "💪", label: "근력" },
  { value: "CYCLING", emoji: "🚴", label: "자전거" },
  { value: "SWIMMING", emoji: "🏊", label: "수영" },
  { value: "OTHER", emoji: "🏋️", label: "기타" },
];

interface WizardStep3Props {
  value: ExerciseSubType | null;
  onChange: (sub: ExerciseSubType) => void;
}

export default function WizardStep3({ value, onChange }: WizardStep3Props) {
  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">운동 종류</h2>
      <p className="text-sm text-text-secondary mb-6">
        어떤 운동을 할 예정인가요?
      </p>

      <div className="grid grid-cols-3 gap-3">
        {EXERCISE_OPTIONS.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              className={[
                "flex flex-col items-center gap-2 p-4 rounded-[14px] border-2 transition-all duration-150",
                isSelected
                  ? "border-brand-black bg-white shadow-sm"
                  : "border-border bg-white hover:border-brand",
              ].join(" ")}
              aria-pressed={isSelected}
              aria-label={opt.label}
            >
              <span className="text-3xl" aria-hidden="true">
                {opt.emoji}
              </span>
              <span className="text-xs font-medium text-text-secondary">
                {opt.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
