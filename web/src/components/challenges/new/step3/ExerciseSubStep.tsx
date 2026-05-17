"use client";

import type { ExerciseSubType } from "@/types/challenge";

/* =========================================
   Step3 — EXERCISE 카테고리: 운동 종류 선택
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
  { value: "OTHER", emoji: "🏋️", label: "기타 운동" },
];

interface ExerciseSubStepProps {
  value: ExerciseSubType | null;
  onChange: (sub: ExerciseSubType) => void;
}

export default function ExerciseSubStep({
  value,
  onChange,
}: ExerciseSubStepProps) {
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
                "flex flex-col items-center gap-2 p-4 rounded-[14px] border-2 transition-all",
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
