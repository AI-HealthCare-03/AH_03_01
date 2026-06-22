"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import StatusBadge from "@/components/health/StatusBadge";
import { getBloodPressureStatus, getFastingGlucoseStatus } from "@/lib/health/status";
import type { WizardFormStep2 } from "@/types/health";

interface StepVitalsProps {
  defaultValues?: Partial<WizardFormStep2>;
  onSubmit: (data: WizardFormStep2) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

export default function StepVitals({ defaultValues, onSubmit, onSkip, isLoading }: StepVitalsProps) {
  const [systolic, setSystolic] = useState(defaultValues?.systolic ?? "");
  const [diastolic, setDiastolic] = useState(defaultValues?.diastolic ?? "");
  const [env, setEnv] = useState<"HOME" | "HOSPITAL">(defaultValues?.measurement_env ?? "HOME");
  const [fasting, setFasting] = useState(defaultValues?.fasting_glucose ?? "");

  const sysParsed = systolic ? parseFloat(systolic) : null;
  const bpStatus = sysParsed !== null ? getBloodPressureStatus(sysParsed) : null;

  const fastingParsed = fasting ? parseFloat(fasting) : null;
  const fastingStatus = fastingParsed !== null ? getFastingGlucoseStatus(fastingParsed) : null;

  const canSubmit = systolic !== "" && diastolic !== "";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit({ systolic, diastolic, measurement_env: env, fasting_glucose: fasting });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">혈압 / 공복혈당</h2>
          <p className="text-sm text-text-secondary mt-0.5">선택 입력 — 건너뛸 수 있습니다.</p>
        </div>

        {/* 측정 환경 */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-2">혈압 측정 환경</p>
          <div className="flex gap-2">
            {([
              { v: "HOME" as const, label: "가정" },
              { v: "HOSPITAL" as const, label: "병원" },
            ] as const).map(({ v, label }) => (
              <button
                key={v}
                type="button"
                onClick={() => setEnv(v)}
                className={[
                  "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
                  env === v
                    ? "bg-brand-black text-white border-brand-black"
                    : "bg-white text-text-secondary border-border",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>
          {env === "HOME" && (
            <p className="mt-1.5 text-xs text-text-tertiary">
              가정 측정 시 수축기/이완기 +5/+5 mmHg 자동 보정됩니다.
            </p>
          )}
        </div>

        {/* 수축기 / 이완기 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="systolic" className="text-sm font-medium text-text-primary mb-1 block">
              수축기
            </label>
            <div className="relative">
              <input
                id="systolic"
                type="number"
                inputMode="numeric"
                placeholder="120"
                value={systolic}
                onChange={(e) => setSystolic(e.target.value)}
                className="w-full h-12 px-4 pr-16 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
                mmHg
              </span>
            </div>
          </div>
          <div>
            <label htmlFor="diastolic" className="text-sm font-medium text-text-primary mb-1 block">
              이완기
            </label>
            <div className="relative">
              <input
                id="diastolic"
                type="number"
                inputMode="numeric"
                placeholder="80"
                value={diastolic}
                onChange={(e) => setDiastolic(e.target.value)}
                className="w-full h-12 px-4 pr-16 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
                mmHg
              </span>
            </div>
          </div>
        </div>

        {bpStatus && (
          <div className="flex items-center gap-2 p-3 bg-surface rounded-[10px]">
            <span className="text-sm text-text-secondary">혈압 판정:</span>
            <StatusBadge status={bpStatus} size="md" />
          </div>
        )}

        {/* 공복혈당 */}
        <div>
          <label htmlFor="fasting_glucose" className="text-sm font-medium text-text-primary mb-1 block">
            공복혈당 <span className="text-text-tertiary font-normal">(선택)</span>
          </label>
          <div className="relative">
            <input
              id="fasting_glucose"
              type="number"
              inputMode="decimal"
              placeholder="100"
              value={fasting}
              onChange={(e) => setFasting(e.target.value)}
              className="w-full h-12 px-4 pr-16 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
              mg/dL
            </span>
          </div>
          {fastingStatus && (
            <div className="flex items-center gap-2 mt-1.5">
              <StatusBadge status={fastingStatus} />
              <span className="text-xs text-text-tertiary">
                정상: 100 미만 / 전당뇨: 100~125 / 당뇨: 126 이상
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Button type="submit" fullWidth loading={isLoading} disabled={!canSubmit}>
          저장 후 다음
        </Button>
        <Button type="button" variant="ghost" fullWidth onClick={onSkip} disabled={isLoading}>
          이 단계 건너뛰기
        </Button>
      </div>
    </form>
  );
}
