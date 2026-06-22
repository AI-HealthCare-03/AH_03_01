"use client";

import {
  Chips,
  DurationPicker,
  WeeklyDurationNote,
  TitleInput,
  MaxParticipantsChips,
  RewardPreview,
  Step4Header,
  GROUP_SUM_OPTIONS,
  WEEKLY_COUNT_OPTIONS,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   WATER 카테고리 Step4 폼
   - WaterDailyForm   (개인 DAILY)
   - WaterWeeklyForm  (개인 WEEKLY_COUNT)
   - WaterGroupForm   (그룹 GROUP_SUM)
   ========================================= */

const WATER_AMOUNT_OPTIONS = [
  { value: 500, label: "500 mL" },
  { value: 1000, label: "1,000 mL" },
  { value: 1500, label: "1,500 mL" },
  { value: 2000, label: "2,000 mL" },
];

/* ─── 공통 양 선택 ─── */
function WaterAmountPicker({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (v: number) => void;
}) {
  return (
    <Chips
      label="하루 목표 용량"
      options={WATER_AMOUNT_OPTIONS}
      value={value}
      onChange={onChange}
    />
  );
}

/* ─── 개인 DAILY ─── */
export function WaterDailyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <WaterAmountPicker
        value={form.goal_config.amount?.value}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, amount: { value: v, unit: "mL" } } })
        }
      />
      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

/* ─── 개인 WEEKLY_COUNT ─── */
export function WaterWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <WaterAmountPicker
        value={form.goal_config.amount?.value}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, amount: { value: v, unit: "mL" } } })
        }
      />
      <Chips
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, weekly_target_count: v } })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

/* ─── 그룹 GROUP_SUM ─── */
export function WaterGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <WaterAmountPicker
        value={form.goal_config.amount?.value}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, amount: { value: v, unit: "mL" } } })
        }
      />
      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, group_target_count: v } })
        }
      />
      <WeeklyDurationNote />
      <MaxParticipantsChips
        value={form.max_participants}
        onChange={(v) => onChange({ max_participants: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup />
    </div>
  );
}
