"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Button from "@/components/ui/Button";
import type { WizardFormStep5 } from "@/types/health";

/* ── 검증 스키마 ─────────────────────────── */

const schema = z.object({
  sleep_weekday: z.string().optional(),
  sleep_weekend: z.string().optional(),
  moderate_exercise_hour: z.string().optional(),
  mid_act_day: z.string().optional(),
  walk_day: z.string().optional(),
  water_count: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/* ── 공통 NumberField ───────────────────── */

function NumberField({
  label,
  id,
  unit,
  placeholder,
  hint,
  value,
  onChange,
}: {
  label: string;
  id: string;
  unit: string;
  placeholder: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium text-text-primary mb-1 block">
        {label}
      </label>
      {hint && <p className="text-xs text-text-tertiary mb-1">{hint}</p>}
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-12 px-4 pr-14 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
        />
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary">
          {unit}
        </span>
      </div>
    </div>
  );
}

/* ── 메인 ────────────────────────────────── */

interface StepActivityProps {
  defaultValues?: Partial<WizardFormStep5>;
  onSubmit: (data: WizardFormStep5) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

export default function StepActivity({ defaultValues, onSubmit, onSkip, isLoading }: StepActivityProps) {
  const { control, handleSubmit } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      sleep_weekday: defaultValues?.sleep_weekday ?? "",
      sleep_weekend: defaultValues?.sleep_weekend ?? "",
      moderate_exercise_hour: defaultValues?.moderate_exercise_hour ?? "",
      mid_act_day: defaultValues?.mid_act_day ?? "",
      walk_day: defaultValues?.walk_day ?? "",
      water_count: defaultValues?.water_count ?? "",
    },
  });

  const onValid = (data: FormValues) => {
    onSubmit({
      sleep_weekday: data.sleep_weekday ?? "",
      sleep_weekend: data.sleep_weekend ?? "",
      moderate_exercise_hour: data.moderate_exercise_hour ?? "",
      mid_act_day: data.mid_act_day ?? "",
      walk_day: data.walk_day ?? "",
      water_count: data.water_count ?? "",
    });
  };

  return (
    <form onSubmit={handleSubmit(onValid)} className="space-y-5">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">수면 · 운동 · 수분</h2>
          <p className="text-sm text-text-secondary mt-0.5">선택 입력 — 건너뛸 수 있습니다.</p>
        </div>

        {/* 수면 */}
        <div className="space-y-1">
          <p className="text-sm font-semibold text-text-primary">수면</p>
          <div className="grid grid-cols-2 gap-4">
            <Controller
              name="sleep_weekday"
              control={control}
              render={({ field }) => (
                <NumberField
                  label="주중 하루 평균"
                  id="sleep_weekday"
                  unit="시간"
                  placeholder="7"
                  hint="소수 허용 (예: 6.5)"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                />
              )}
            />
            <Controller
              name="sleep_weekend"
              control={control}
              render={({ field }) => (
                <NumberField
                  label="주말 하루 평균"
                  id="sleep_weekend"
                  unit="시간"
                  placeholder="8"
                  hint="소수 허용 (예: 7.5)"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                />
              )}
            />
          </div>
        </div>

        <div className="h-px bg-border" />

        {/* 운동 */}
        <div className="space-y-4">
          <p className="text-sm font-semibold text-text-primary">운동</p>
          <p className="text-xs text-text-tertiary -mt-2">
            중강도 운동: 빠른 걷기, 자전거, 수영, 청소 등 약간 숨이 찰 정도
          </p>
          <Controller
            name="mid_act_day"
            control={control}
            render={({ field }) => (
              <NumberField
                label="일주일에 중강도 운동을 며칠 하시나요?"
                id="mid_act_day"
                unit="일"
                placeholder="3"
                value={field.value ?? ""}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            name="moderate_exercise_hour"
            control={control}
            render={({ field }) => (
              <NumberField
                label="중강도 운동을 하는 날 하루 평균 몇 시간?"
                id="moderate_exercise_hour"
                unit="시간"
                placeholder="1"
                hint="소수 허용 (예: 0.5 = 30분)"
                value={field.value ?? ""}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            name="walk_day"
            control={control}
            render={({ field }) => (
              <NumberField
                label="최근 1주일 중 10분 이상 걸은 날은 며칠?"
                id="walk_day"
                unit="일"
                placeholder="5"
                value={field.value ?? ""}
                onChange={field.onChange}
              />
            )}
          />
        </div>

        <div className="h-px bg-border" />

        {/* 수분 */}
        <Controller
          name="water_count"
          control={control}
          render={({ field }) => (
            <NumberField
              label="하루에 물(차 포함)을 몇 컵 드시나요?"
              id="water_count"
              unit="컵"
              placeholder="8"
              hint="1컵 = 200ml 기준"
              value={field.value ?? ""}
              onChange={field.onChange}
            />
          )}
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
