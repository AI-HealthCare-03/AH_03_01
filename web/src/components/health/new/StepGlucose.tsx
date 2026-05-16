"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import StatusBadge from "@/components/health/StatusBadge";
import { getFastingGlucoseStatus, getHba1cStatus } from "@/lib/health/status";
import type { WizardFormStep3 } from "@/types/health";

interface StepGlucoseProps {
  onSubmit: (data: WizardFormStep3) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

interface GlucoseFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  unit: string;
  placeholder: string;
  statusNode?: React.ReactNode;
}

function GlucoseField({ id, label, value, onChange, unit, placeholder, statusNode }: GlucoseFieldProps) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="text-sm font-medium text-text-primary block">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-12 px-4 pr-16 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
          {unit}
        </span>
      </div>
      {statusNode}
    </div>
  );
}

export default function StepGlucose({ onSubmit, onSkip, isLoading }: StepGlucoseProps) {
  const [fasting, setFasting] = useState("");
  const [postmeal, setPostmeal] = useState("");
  const [hba1c, setHba1c] = useState("");

  const fastingStatus = fasting ? getFastingGlucoseStatus(parseFloat(fasting)) : null;
  const hba1cStatus = hba1c ? getHba1cStatus(parseFloat(hba1c)) : null;

  const hasAnyInput = fasting !== "" || postmeal !== "" || hba1c !== "";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ fasting_glucose: fasting, postmeal_glucose: postmeal, hba1c });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">혈당 / HbA1c</h2>
          <p className="text-sm text-text-secondary mt-0.5">
            선택 입력 — 입력된 항목만 저장됩니다.
          </p>
        </div>

        <GlucoseField
          id="fasting_glucose"
          label="공복혈당"
          value={fasting}
          onChange={setFasting}
          unit="mg/dL"
          placeholder="100"
          statusNode={
            fastingStatus ? (
              <div className="flex items-center gap-2 mt-1">
                <StatusBadge status={fastingStatus} />
                <span className="text-xs text-text-tertiary">
                  (정상: 100 미만 / 전당뇨: 100~125 / 당뇨: 126 이상)
                </span>
              </div>
            ) : undefined
          }
        />

        <GlucoseField
          id="postmeal_glucose"
          label="식후혈당 (식후 2시간)"
          value={postmeal}
          onChange={setPostmeal}
          unit="mg/dL"
          placeholder="140"
        />

        <GlucoseField
          id="hba1c"
          label="당화혈색소 (HbA1c)"
          value={hba1c}
          onChange={setHba1c}
          unit="%"
          placeholder="5.7"
          statusNode={
            hba1cStatus ? (
              <div className="flex items-center gap-2 mt-1">
                <StatusBadge status={hba1cStatus} />
                <span className="text-xs text-text-tertiary">
                  (정상: 5.7% 미만 / 전당뇨: 5.7~6.4% / 당뇨: 6.5% 이상)
                </span>
              </div>
            ) : undefined
          }
        />
      </div>

      <div className="rounded-[12px] bg-[#fffbe6] border border-[#f9e000] p-3 text-xs text-[#856404]">
        마지막 단계입니다. 저장 후 자동으로 위험도를 계산합니다.
        계산에 실패해도 기록은 저장됩니다.
      </div>

      <div className="flex flex-col gap-2">
        <Button
          type="submit"
          fullWidth
          loading={isLoading}
          disabled={!hasAnyInput && !isLoading}
        >
          저장 & 위험도 계산
        </Button>
        <Button
          type="button"
          variant="ghost"
          fullWidth
          onClick={onSkip}
          disabled={isLoading}
        >
          건너뛰고 위험도 계산
        </Button>
      </div>
    </form>
  );
}
