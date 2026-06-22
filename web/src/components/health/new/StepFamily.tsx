"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import type { WizardFormStep3 } from "@/types/health";

interface StepFamilyProps {
  defaultValues?: Partial<WizardFormStep3>;
  onSubmit: (data: WizardFormStep3) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

/* 1=있음 / 0=없음 / -1=모름 */
type TriState = 1 | 0 | -1;

const OPTIONS: { value: TriState; label: string }[] = [
  { value: 1, label: "있음" },
  { value: 0, label: "없음" },
  { value: -1, label: "모름" },
];

function TriField({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description?: string;
  value: TriState;
  onChange: (v: TriState) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-0.5">{label}</p>
      {description && <p className="text-xs text-text-tertiary mb-2">{description}</p>}
      <div className="flex gap-2">
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
              value === opt.value
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function StepFamily({ defaultValues, onSubmit, onSkip, isLoading }: StepFamilyProps) {
  const [familyDm, setFamilyDm] = useState<TriState>((defaultValues?.family_dm as TriState) ?? -1);
  const [familyHp, setFamilyHp] = useState<TriState>((defaultValues?.family_hp as TriState) ?? -1);
  const [familyHl, setFamilyHl] = useState<TriState>((defaultValues?.family_hl as TriState) ?? -1);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ family_dm: familyDm, family_hp: familyHp, family_hl: familyHl });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">가족력</h2>
          <p className="text-sm text-text-secondary mt-0.5">
            부모·형제 중 해당 질환이 있는지 알려주세요.
          </p>
        </div>

        <TriField
          label="당뇨 가족력"
          value={familyDm}
          onChange={setFamilyDm}
        />
        <TriField
          label="고혈압 가족력"
          value={familyHp}
          onChange={setFamilyHp}
        />
        <TriField
          label="고지혈증 가족력"
          value={familyHl}
          onChange={setFamilyHl}
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
