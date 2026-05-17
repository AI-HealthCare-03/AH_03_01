"use client";

import {
  Chips,
  DurationPicker,
  WeeklyDurationNote,
  TitleInput,
  MaxParticipantsSlider,
  RewardPreview,
  Step4Header,
  GROUP_MEMBERS_OPTIONS,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   NO_SMOKING / NO_ALCOHOL 카테고리 Step4 폼
   - NoSmokingForm       (개인 DAILY)
   - NoSmokingWeeklyForm (개인 WEEKLY_COUNT)
   - NoSmokingGroupForm  (그룹 GROUP_MEMBERS)
   - NoAlcoholForm       (개인 DAILY)
   - NoAlcoholWeeklyForm (개인 WEEKLY_COUNT)
   - NoAlcoholGroupForm  (그룹 GROUP_MEMBERS)

   금연/금주 그룹은 GROUP_MEMBERS (달성 인원 기준)
   ========================================= */

/* 그룹 금연/금주 기간 옵션 */
const GROUP_DURATION_OPTIONS = [
  { value: 14, label: "2주" },
  { value: 30, label: "1개월" },
  { value: 60, label: "2개월" },
] as const;

function GroupDurationPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: 7 | 14 | 30) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-primary mb-2">
        챌린지 기간
      </label>
      <div className="flex gap-2">
        {GROUP_DURATION_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value as 7 | 14 | 30)}
            className={[
              "flex-1 py-2.5 rounded-[10px] text-sm font-semibold border-2 transition-all",
              value === opt.value
                ? "border-brand-black bg-brand text-brand-black"
                : "border-border bg-white text-text-secondary hover:border-brand",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* 공통 CHECK 안내 */
function CheckNote({ label }: { label: string }) {
  return (
    <div className="p-3 bg-surface rounded-[10px]">
      <p className="text-xs text-text-secondary">
        인증 방식: 매일 {label} 여부 체크 (사진 불필요)
      </p>
    </div>
  );
}

/* ─── 개인 금연 DAILY ─── */
export function NoSmokingForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <CheckNote label="금연" />
      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

/* ─── 개인 금연 WEEKLY_COUNT ─── */
const WEEKLY_NOSMOKING_OPTIONS = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
  value: n,
  label: `주 ${n}회`,
}));

export function NoSmokingWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <CheckNote label="금연" />
      <Chips
        label="주간 금연 목표 일수"
        options={WEEKLY_NOSMOKING_OPTIONS}
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

/* ─── 그룹 금연 GROUP_MEMBERS ─── */
export function NoSmokingGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <CheckNote label="금연" />
      <Chips
        label="그룹 달성 목표 인원"
        options={GROUP_MEMBERS_OPTIONS}
        value={form.goal_config.group_target_members}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, group_target_members: v } })
        }
      />
      <GroupDurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <MaxParticipantsSlider
        value={form.max_participants}
        onChange={(v) => onChange({ max_participants: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup />
    </div>
  );
}

/* ─── 개인 금주 DAILY ─── */
export function NoAlcoholForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <CheckNote label="금주" />
      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

/* ─── 개인 금주 WEEKLY_COUNT ─── */
export function NoAlcoholWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <CheckNote label="금주" />
      <Chips
        label="주간 금주 목표 일수"
        options={WEEKLY_NOSMOKING_OPTIONS}
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

/* ─── 그룹 금주 GROUP_MEMBERS ─── */
export function NoAlcoholGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <CheckNote label="금주" />
      <Chips
        label="그룹 달성 목표 인원"
        options={GROUP_MEMBERS_OPTIONS}
        value={form.goal_config.group_target_members}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, group_target_members: v } })
        }
      />
      <GroupDurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <MaxParticipantsSlider
        value={form.max_participants}
        onChange={(v) => onChange({ max_participants: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup />
    </div>
  );
}
