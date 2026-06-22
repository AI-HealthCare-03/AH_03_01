"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import type { WizardFormStep6 } from "@/types/health";

interface StepDietProps {
  defaultValues?: Partial<WizardFormStep6>;
  onSubmit: (data: WizardFormStep6) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

/* LS_VEG1 / LS_FRUIT (1~9) */
const VEG_FRUIT_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "하루 3회 이상" },
  { value: 2, label: "하루 2회" },
  { value: 3, label: "하루 1회" },
  { value: 4, label: "주 5~6회" },
  { value: 5, label: "주 2~4회" },
  { value: 6, label: "주 1회" },
  { value: 7, label: "월 2~3회" },
  { value: 8, label: "월 1회" },
  { value: 9, label: "거의 안 먹음" },
];

/* L_OUT_FQ (1~7) */
const OUT_MEAL_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "하루 2회 이상" },
  { value: 2, label: "하루 1회" },
  { value: 3, label: "주 5~6회" },
  { value: 4, label: "주 3~4회" },
  { value: 5, label: "주 1~2회" },
  { value: 6, label: "월 1~3회" },
  { value: 7, label: "거의 안 함" },
];

/* L_BR_FQ (1~4) */
const BREAKFAST_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "주 5~7회" },
  { value: 2, label: "주 3~4회" },
  { value: 3, label: "주 1~2회" },
  { value: 4, label: "거의 안 함" },
];

function SelectDropdown({
  label,
  id,
  hint,
  options,
  value,
  onChange,
}: {
  label: string;
  id: string;
  hint?: string;
  options: { value: number; label: string }[];
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium text-text-primary mb-1 block">
        {label}
      </label>
      {hint && <p className="text-xs text-text-tertiary mb-1.5">{hint}</p>}
      <select
        id={id}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="w-full h-12 px-4 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors appearance-none"
      >
        <option value="">선택해 주세요</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function StepDiet({ defaultValues, onSubmit, onSkip, isLoading }: StepDietProps) {
  const [vegFreq, setVegFreq] = useState<number | null>(defaultValues?.veg_freq_1 ?? null);
  const [fruitFreq, setFruitFreq] = useState<number | null>(defaultValues?.fruit_freq ?? null);
  const [outMealFreq, setOutMealFreq] = useState<number | null>(defaultValues?.out_meal_freq ?? null);
  const [breakfastFreq, setBreakfastFreq] = useState<number | null>(defaultValues?.breakfast_freq ?? null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      veg_freq_1: vegFreq,
      fruit_freq: fruitFreq,
      out_meal_freq: outMealFreq,
      breakfast_freq: breakfastFreq,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">식습관</h2>
          <p className="text-sm text-text-secondary mt-0.5">선택 입력 — 건너뛸 수 있습니다.</p>
        </div>

        <SelectDropdown
          label="채소·버섯·해조류를 평균 얼마나 드시나요?"
          id="veg_freq"
          hint="반찬·국·김치 포함"
          options={VEG_FRUIT_OPTIONS}
          value={vegFreq}
          onChange={setVegFreq}
        />

        <SelectDropdown
          label="과일을 평균 얼마나 드시나요?"
          id="fruit_freq"
          options={VEG_FRUIT_OPTIONS}
          value={fruitFreq}
          onChange={setFruitFreq}
        />

        <SelectDropdown
          label="외식(배달·포장·급식 포함)은 얼마나 자주 하시나요?"
          id="out_meal_freq"
          options={OUT_MEAL_OPTIONS}
          value={outMealFreq}
          onChange={setOutMealFreq}
        />

        <SelectDropdown
          label="아침식사를 일주일에 몇 회 하시나요?"
          id="breakfast_freq"
          options={BREAKFAST_OPTIONS}
          value={breakfastFreq}
          onChange={setBreakfastFreq}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Button type="submit" fullWidth loading={isLoading}>
          저장 후 다음
        </Button>
        <Button type="button" variant="ghost" fullWidth onClick={onSkip} disabled={isLoading}>
          이 단계 건너뛰기
        </Button>
      </div>
    </form>
  );
}
