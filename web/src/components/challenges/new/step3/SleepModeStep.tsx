"use client";

/* =========================================
   Step3 — SLEEP 카테고리: 수면 모드 선택
   BED_TIME / SLEEP_DURATION / WAKE_TIME
   ========================================= */

export type SleepMode = "BED_TIME" | "SLEEP_DURATION" | "WAKE_TIME";

interface SleepModeStepProps {
  value: SleepMode | null;
  onChange: (mode: SleepMode) => void;
}

const SLEEP_OPTIONS: {
  value: SleepMode;
  emoji: string;
  title: string;
  desc: string;
}[] = [
  {
    value: "BED_TIME",
    emoji: "🌙",
    title: "잠드는 시간",
    desc: "목표 취침 시간대에 맞춰 잠들기",
  },
  {
    value: "SLEEP_DURATION",
    emoji: "💤",
    title: "수면 시간",
    desc: "하루 7시간 이상 수면",
  },
  {
    value: "WAKE_TIME",
    emoji: "⏰",
    title: "기상 시간",
    desc: "아침 7시 또는 8시에 일어나기",
  },
];

export default function SleepModeStep({ value, onChange }: SleepModeStepProps) {
  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">수면 목표</h2>
      <p className="text-sm text-text-secondary mb-6">
        어떤 수면 습관을 개선하고 싶으신가요?
      </p>

      <div className="grid grid-cols-1 gap-3">
        {SLEEP_OPTIONS.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              className={[
                "flex items-center gap-4 p-4 rounded-[14px] border-2 transition-all text-left",
                isSelected
                  ? "border-brand-black bg-white shadow-sm"
                  : "border-border bg-white hover:border-brand",
              ].join(" ")}
              aria-pressed={isSelected}
            >
              <span className="text-3xl shrink-0" aria-hidden="true">
                {opt.emoji}
              </span>
              <div>
                <p className="font-semibold text-text-primary">{opt.title}</p>
                <p className="text-xs text-text-secondary mt-0.5">{opt.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
