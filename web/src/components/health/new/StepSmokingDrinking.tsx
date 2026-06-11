"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import type { WizardFormStep4 } from "@/types/health";

interface StepSmokingDrinkingProps {
  onSubmit: (data: WizardFormStep4) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

type SmokingChoice = "CURRENT" | "QUIT" | "NEVER";

const SMOKING_OPTIONS: { value: SmokingChoice; label: string; sub?: string }[] = [
  { value: "CURRENT", label: "현재 흡연 중", sub: "일반·전자담배·액상형 포함" },
  { value: "QUIT", label: "과거에 피웠으나 현재 안 함" },
  { value: "NEVER", label: "한 번도 피운 적 없음" },
];

/* BD1_11 코드 (alcohol_freq_y) */
const ALCOHOL_FREQ_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "전혀 안 마심" },
  { value: 2, label: "월 1회 미만" },
  { value: 3, label: "월 1회 정도" },
  { value: 4, label: "월 2~4회" },
  { value: 5, label: "주 2~3회" },
  { value: 6, label: "주 4회 이상" },
];

/* BD2_1 코드 (alcohol_cup) */
const ALCOHOL_CUP_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "1~2잔" },
  { value: 2, label: "3~4잔" },
  { value: 3, label: "5~6잔" },
  { value: 4, label: "7~9잔" },
  { value: 5, label: "10잔 이상" },
];

function SelectChip<T extends number | string>({
  label,
  options,
  value,
  onChange,
  cols = 3,
}: {
  label: string;
  options: { value: T; label: string; sub?: string }[];
  value: T | null;
  onChange: (v: T) => void;
  cols?: 2 | 3;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">{label}</p>
      <div className={`grid gap-2 ${cols === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
        {options.map((opt) => (
          <button
            key={String(opt.value)}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "px-3 py-2.5 text-sm rounded-[10px] border transition-colors min-h-[44px] text-left",
              value === opt.value
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            <span className="block leading-snug">{opt.label}</span>
            {opt.sub && (
              <span className={[
                "block text-[11px] mt-0.5",
                value === opt.value ? "text-white/70" : "text-text-tertiary",
              ].join(" ")}>
                {opt.sub}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function StepSmokingDrinking({ onSubmit, onSkip, isLoading }: StepSmokingDrinkingProps) {
  const [smokingChoice, setSmokingChoice] = useState<SmokingChoice | null>(null);
  const [alcoholFreq, setAlcoholFreq] = useState<number | null>(null);
  const [alcoholCup, setAlcoholCup] = useState<number | null>(null);

  /* alcohol_freq_y=1(전혀 안 마심) 이면 음주량 질문 숨김 */
  const isNonDrinker = alcoholFreq === 1;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!smokingChoice) return;
    onSubmit({
      smoking_choice: smokingChoice,
      alcohol_freq_y: alcoholFreq,
      alcohol_cup: isNonDrinker ? null : alcoholCup,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-6">
        <div>
          <h2 className="font-bold text-lg text-text-primary">흡연 · 음주</h2>
          <p className="text-sm text-text-secondary mt-0.5">선택 입력 — 건너뛸 수 있습니다.</p>
        </div>

        {/* 흡연 */}
        <SelectChip
          label="현재 흡연 상태를 알려주세요"
          options={SMOKING_OPTIONS}
          value={smokingChoice}
          onChange={(v) => setSmokingChoice(v as SmokingChoice)}
          cols={3}
        />

        <div className="h-px bg-border" />

        {/* 음주 빈도 */}
        <SelectChip
          label="최근 1년간 술을 얼마나 자주 드셨나요?"
          options={ALCOHOL_FREQ_OPTIONS}
          value={alcoholFreq}
          onChange={(v) => {
            setAlcoholFreq(v as number);
            if (v === 1) setAlcoholCup(null);
          }}
          cols={3}
        />

        {/* 음주량 — 전혀 안 마심이 아닐 때만 노출 */}
        {alcoholFreq !== null && !isNonDrinker && (
          <SelectChip
            label="한 번에 보통 몇 잔 정도 드시나요?"
            options={ALCOHOL_CUP_OPTIONS}
            value={alcoholCup}
            onChange={(v) => setAlcoholCup(v as number)}
            cols={3}
          />
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Button
          type="submit"
          fullWidth
          loading={isLoading}
          disabled={smokingChoice === null}
        >
          저장 후 다음
        </Button>
        <Button type="button" variant="ghost" fullWidth onClick={onSkip} disabled={isLoading}>
          이 단계 건너뛰기
        </Button>
      </div>
    </form>
  );
}
