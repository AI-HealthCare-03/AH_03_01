"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Button from "@/components/ui/Button";
import WaistPopover from "@/components/health/WaistPopover";
import type { WizardFormStep1 } from "@/types/health";

/* ── 검증 스키마 ─────────────────────────── */

const schema = z.object({
  height_cm: z.string().optional(),
  weight_kg: z.string().optional(),
  waist_cm: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/* ── 공통 NumberField (StepBasic 패턴 재사용) ─ */

function NumberField({
  label,
  id,
  unit,
  placeholder,
  value,
  onChange,
  helpTip,
}: {
  label: string;
  id: string;
  unit: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  helpTip?: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="flex items-center gap-1 text-sm font-medium text-text-primary mb-1">
        {label}
        {helpTip}
      </label>
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-12 px-4 pr-12 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
        />
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary">
          {unit}
        </span>
      </div>
    </div>
  );
}

/* ── 메인 ────────────────────────────────── */

interface StepMeasureProps {
  defaultValues?: Partial<WizardFormStep1>;
  onSubmit: (data: WizardFormStep1) => void;
  isLoading?: boolean;
}

export default function StepMeasure({ defaultValues, onSubmit, isLoading }: StepMeasureProps) {
  const { control, handleSubmit } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      height_cm: defaultValues?.height_cm ?? "",
      weight_kg: defaultValues?.weight_kg ?? "",
      waist_cm: defaultValues?.waist_cm ?? "",
    },
  });

  const onValid = (data: FormValues) => {
    onSubmit({
      height_cm: data.height_cm ?? "",
      weight_kg: data.weight_kg ?? "",
      waist_cm: data.waist_cm ?? "",
    });
  };

  return (
    <form onSubmit={handleSubmit(onValid)} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">신체 계측</h2>
          <p className="text-sm text-text-secondary mt-0.5">
            위험도 계산에 활용됩니다. 최대한 정확히 입력해 주세요.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Controller
            name="height_cm"
            control={control}
            render={({ field }) => (
              <NumberField
                label="키"
                id="height_cm"
                unit="cm"
                placeholder="170"
                value={field.value ?? ""}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            name="weight_kg"
            control={control}
            render={({ field }) => (
              <NumberField
                label="몸무게"
                id="weight_kg"
                unit="kg"
                placeholder="65"
                value={field.value ?? ""}
                onChange={field.onChange}
              />
            )}
          />
        </div>

        <Controller
          name="waist_cm"
          control={control}
          render={({ field }) => (
            <NumberField
              label="허리둘레"
              id="waist_cm"
              unit="cm"
              placeholder="80"
              value={field.value ?? ""}
              onChange={field.onChange}
              helpTip={<WaistPopover isMobile />}
            />
          )}
        />
      </div>

      <Button type="submit" fullWidth loading={isLoading}>
        저장 후 다음
      </Button>
    </form>
  );
}
