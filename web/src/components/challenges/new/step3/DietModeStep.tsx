"use client";

/* =========================================
   Step3 — DIET 카테고리
   개인: AVOID / INCLUDE / WEIGHT
   그룹: 식단 종류 선택 (MEDITERRANEAN 등)
   ========================================= */

export type DietPersonalMode = "AVOID" | "INCLUDE" | "WEIGHT";

interface DietModeStepProps {
  scope: "PERSONAL" | "GROUP";
  value: DietPersonalMode | string | null;
  onChange: (v: string) => void;
}

const PERSONAL_OPTIONS: {
  value: DietPersonalMode;
  emoji: string;
  title: string;
  desc: string;
}[] = [
  {
    value: "AVOID",
    emoji: "🚫",
    title: "특정 음식 피하기",
    desc: "기름진 음식, 패스트푸드 등 회피 목표",
  },
  {
    value: "INCLUDE",
    emoji: "✅",
    title: "특정 음식 먹기",
    desc: "채소, 과일, 생선 등 건강 식품 섭취",
  },
  {
    value: "WEIGHT",
    emoji: "⚖️",
    title: "체중 관리",
    desc: "감량 목표 또는 체중 유지",
  },
];

const GROUP_OPTIONS: { value: string; emoji: string; title: string; desc: string }[] = [
  { value: "MEDITERRANEAN", emoji: "🫒", title: "지중해식", desc: "올리브오일, 채소, 생선 중심" },
  { value: "LOW_CARB", emoji: "🥩", title: "저탄수", desc: "탄수화물을 줄인 식단" },
  { value: "LOW_FAT", emoji: "🥗", title: "저지방", desc: "지방 섭취를 줄인 식단" },
  { value: "LOW_SODIUM", emoji: "🧂", title: "저염", desc: "나트륨을 줄인 식단" },
  { value: "LOW_SUGAR", emoji: "🍬", title: "저당", desc: "당류를 줄인 식단" },
];

export default function DietModeStep({ scope, value, onChange }: DietModeStepProps) {
  const options = scope === "PERSONAL" ? PERSONAL_OPTIONS : GROUP_OPTIONS;

  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">식단 목표</h2>
      <p className="text-sm text-text-secondary mb-6">
        {scope === "PERSONAL"
          ? "어떤 식습관을 만들어 가고 싶으신가요?"
          : "그룹이 함께 실천할 식단을 선택해 주세요."}
      </p>

      <div className="grid grid-cols-1 gap-3">
        {options.map((opt) => {
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
