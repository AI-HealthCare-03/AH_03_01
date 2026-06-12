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
   MEDITATION 카테고리 Step4 폼
   - MeditationDailyForm   (개인 DAILY)
   - MeditationWeeklyForm  (개인 WEEKLY_COUNT)
   - MeditationGroupForm   (그룹 GROUP_SUM)
   ========================================= */

const MEDITATION_DURATION_OPTIONS = [
  { value: 3, label: "3분" },
  { value: 5, label: "5분" },
  { value: 10, label: "10분" },
  { value: 20, label: "20분" },
];

function MeditationDurationPicker({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (v: number) => void;
}) {
  return (
    <Chips
      label="명상 시간"
      options={MEDITATION_DURATION_OPTIONS}
      value={value}
      onChange={onChange}
    />
  );
}

/* ─── 개인 DAILY ─── */
export function MeditationDailyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <MeditationDurationPicker
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, duration_minutes: v } })
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
export function MeditationWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <MeditationDurationPicker
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, duration_minutes: v } })
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
export function MeditationGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <MeditationDurationPicker
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, duration_minutes: v } })
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
      <div className="p-3 bg-surface rounded-[10px]">
        <p className="text-xs text-text-secondary">
          1일 1회만 그룹 성공 횟수로 인정됩니다.
        </p>
      </div>
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
