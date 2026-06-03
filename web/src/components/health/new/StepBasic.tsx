"use client";

import React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Button from "@/components/ui/Button";
import WaistPopover from "@/components/health/WaistPopover";
import type {
  WizardFormStep1,
  SmokingStatus,
  AlcoholFrequency,
  PregnancyStatus,
  ChronicDisease,
} from "@/types/health";

/* ── 검증 스키마 ─────────────────────── */

const schema = z.object({
  height_cm: z.string().optional(),
  weight_kg: z.string().optional(),
  waist_cm: z.string().optional(),
  smoking_status: z.enum(["NEVER", "CURRENT", "QUIT"]),
  alcohol_frequency: z.enum(["NONE", "WEEKLY_1_2", "WEEKLY_3_4", "DAILY"]),
  family_history_diabetes: z.boolean(),
  family_history_hypertension: z.boolean(),
  chronic_diseases: z.array(z.string()),
  pregnancy_status: z.enum(["NONE", "PREGNANT", "POSTPARTUM"]),
});

type FormValues = z.infer<typeof schema>;

/* ── 옵션 목록 ───────────────────────── */

const SMOKING_OPTIONS: { value: SmokingStatus; label: string }[] = [
  { value: "NEVER", label: "비흡연" },
  { value: "CURRENT", label: "현재 흡연" },
  { value: "QUIT", label: "금연 중" },
];

const ALCOHOL_OPTIONS: { value: AlcoholFrequency; label: string }[] = [
  { value: "NONE", label: "없음" },
  { value: "WEEKLY_1_2", label: "주 1~2회" },
  { value: "WEEKLY_3_4", label: "주 3~4회" },
  { value: "DAILY", label: "매일" },
];

const PREGNANCY_OPTIONS: { value: PregnancyStatus; label: string }[] = [
  { value: "NONE", label: "해당 없음" },
  { value: "PREGNANT", label: "임신 중" },
  { value: "POSTPARTUM", label: "산후" },
];

const CHRONIC_OPTIONS: { value: ChronicDisease; label: string }[] = [
  { value: "NONE", label: "없음" },
  { value: "HYPERTENSION", label: "고혈압" },
  { value: "DIABETES", label: "당뇨병" },
  { value: "HYPERLIPIDEMIA", label: "고지혈증" },
  { value: "HEART_DISEASE", label: "심장 질환" },
  { value: "KIDNEY_DISEASE", label: "신장 질환" },
  { value: "OBESITY", label: "비만" },
];

/* ── 공통 입력 ─────────────────────── */

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

function SelectGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "px-3 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
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

function BooleanField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">{label}</p>
      <div className="flex gap-2">
        {[
          { v: true, label: "있음" },
          { v: false, label: "없음" },
        ].map(({ v, label: l }) => (
          <button
            key={String(v)}
            type="button"
            onClick={() => onChange(v)}
            className={[
              "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
              value === v
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── 만성질환 멀티선택 ─────────────── */

function ChronicDiseaseField({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const toggle = (disease: string) => {
    if (disease === "NONE") {
      onChange(["NONE"]);
      return;
    }
    const without = value.filter((d) => d !== "NONE");
    if (without.includes(disease)) {
      const next = without.filter((d) => d !== disease);
      onChange(next.length === 0 ? ["NONE"] : next);
    } else {
      onChange([...without, disease]);
    }
  };

  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">만성질환 (복수 선택)</p>
      <div className="flex flex-wrap gap-2">
        {CHRONIC_OPTIONS.map((opt) => {
          const isSelected =
            opt.value === "NONE" ? value.includes("NONE") : value.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={[
                "px-3 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
                isSelected
                  ? "bg-brand-black text-white border-brand-black"
                  : "bg-white text-text-secondary border-border hover:border-text-primary",
              ].join(" ")}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ── 메인 ────────────────────────────── */

interface StepBasicProps {
  defaultValues?: Partial<WizardFormStep1>;
  onSubmit: (data: WizardFormStep1) => void;
  isLoading?: boolean;
}

export default function StepBasic({ defaultValues, onSubmit, isLoading }: StepBasicProps) {
  const { control, handleSubmit } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      height_cm: defaultValues?.height_cm ?? "",
      weight_kg: defaultValues?.weight_kg ?? "",
      waist_cm: defaultValues?.waist_cm ?? "",
      smoking_status: defaultValues?.smoking_status ?? "NEVER",
      alcohol_frequency: defaultValues?.alcohol_frequency ?? "NONE",
      family_history_diabetes: defaultValues?.family_history_diabetes ?? false,
      family_history_hypertension: defaultValues?.family_history_hypertension ?? false,
      chronic_diseases: defaultValues?.chronic_diseases ?? ["NONE"],
      pregnancy_status: defaultValues?.pregnancy_status ?? "NONE",
    },
  });

  const onValid = (data: FormValues) => {
    onSubmit(data as unknown as WizardFormStep1);
  };

  return (
    <form onSubmit={handleSubmit(onValid)} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <h2 className="font-bold text-lg text-text-primary">기본 정보</h2>

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

        <Controller
          name="smoking_status"
          control={control}
          render={({ field }) => (
            <SelectGroup
              label="흡연"
              options={SMOKING_OPTIONS}
              value={field.value as SmokingStatus}
              onChange={field.onChange}
            />
          )}
        />

        <Controller
          name="alcohol_frequency"
          control={control}
          render={({ field }) => (
            <SelectGroup
              label="알코올"
              options={ALCOHOL_OPTIONS}
              value={field.value as AlcoholFrequency}
              onChange={field.onChange}
            />
          )}
        />

        <Controller
          name="family_history_diabetes"
          control={control}
          render={({ field }) => (
            <BooleanField
              label="당뇨 가족력"
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />

        <Controller
          name="family_history_hypertension"
          control={control}
          render={({ field }) => (
            <BooleanField
              label="고혈압 가족력"
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />

        <Controller
          name="chronic_diseases"
          control={control}
          render={({ field }) => (
            <ChronicDiseaseField value={field.value} onChange={field.onChange} />
          )}
        />

        <Controller
          name="pregnancy_status"
          control={control}
          render={({ field }) => (
            <SelectGroup
              label="임신"
              options={PREGNANCY_OPTIONS}
              value={field.value as PregnancyStatus}
              onChange={field.onChange}
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
