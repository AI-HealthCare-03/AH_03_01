"use client";

/* =========================================
   Step3 — DISEASE_CARE 카테고리: 챌린지 종류 선택
   ========================================= */

const DISEASE_OPTIONS: {
  value: string;
  emoji: string;
  title: string;
  desc: string;
}[] = [
  {
    value: "DIABETIC_FOOT_DAILY",
    emoji: "🦶",
    title: "당뇨발 매일 관리",
    desc: "9문항 설문으로 매일 발 상태 체크",
  },
];

interface DiseaseTypeStepProps {
  value: string | null;
  onChange: (v: string) => void;
}

export default function DiseaseTypeStep({ value, onChange }: DiseaseTypeStepProps) {
  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">질환 관리 종류</h2>
      <p className="text-sm text-text-secondary mb-6">
        관리할 질환 챌린지를 선택해 주세요.
      </p>

      <div className="grid grid-cols-1 gap-3">
        {DISEASE_OPTIONS.map((opt) => {
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

      <p className="mt-4 text-xs text-text-tertiary">
        추가 질환 관리 챌린지는 순차적으로 추가될 예정입니다.
      </p>
    </div>
  );
}
