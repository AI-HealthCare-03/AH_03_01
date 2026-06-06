"use client";

import {
  Chips,
  RadioCards,
  DurationPicker,
  WeeklyDurationNote,
  TitleInput,
  MaxParticipantsSlider,
  RewardPreview,
  Step4Header,
  GROUP_SUM_OPTIONS,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   SLEEP 카테고리 Step4 폼
   - SleepBedTimeForm      (개인 BED_TIME DAILY)
   - SleepDurationForm     (개인 SLEEP_DURATION DAILY)
   - SleepWakeForm         (개인 WAKE_TIME DAILY)
   - SleepGroupForm        (그룹 GROUP_SUM — 모드 선택 포함)
   ========================================= */

const BED_TIME_OPTIONS = [
  { value: "22-23", label: "오후 10~11시" },
  { value: "23-00", label: "오후 11시~자정" },
  { value: "00-01", label: "자정~오전 1시" },
];

const WAKE_TIME_OPTIONS = [
  { value: "07:00", label: "아침 7시" },
  { value: "08:00", label: "아침 8시" },
];

/* ─── 개인 BED_TIME ─── */
export function SleepBedTimeForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <Chips
        label="목표 취침 시간대"
        options={BED_TIME_OPTIONS}
        value={form.goal_config.sleep_time_range}
        onChange={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              sleep_mode: "BED_TIME",
              sleep_time_range: v,
            },
          })
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

/* ─── 개인 SLEEP_DURATION ─── */
export function SleepDurationForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <div className="p-4 bg-surface rounded-[12px]">
        <p className="text-sm font-semibold text-text-primary">목표</p>
        <p className="text-sm text-text-secondary mt-1">
          하루 7시간 이상 수면 — 매일 달성 여부를 기록합니다.
        </p>
      </div>
      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

/* ─── 개인 WAKE_TIME ─── */
export function SleepWakeForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <Chips
        label="목표 기상 시간"
        options={WAKE_TIME_OPTIONS}
        value={form.goal_config.wake_time}
        onChange={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              sleep_mode: "WAKE_TIME",
              wake_time: v,
            },
          })
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

/* ─── 그룹 공통 하단 필드 ─── */
function SleepGroupFooter({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <>
      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, group_target_count: v } })
        }
      />
      <WeeklyDurationNote />
      <MaxParticipantsSlider
        value={form.max_participants}
        onChange={(v) => onChange({ max_participants: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup />
    </>
  );
}

/* ─── 그룹 BED_TIME ─── */
export function SleepGroupBedTimeForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <Chips
        label="목표 취침 시간대"
        options={BED_TIME_OPTIONS}
        value={form.goal_config.sleep_time_range}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, sleep_mode: "BED_TIME", sleep_time_range: v },
          })
        }
      />
      <SleepGroupFooter form={form} onChange={onChange} />
    </div>
  );
}

/* ─── 그룹 SLEEP_DURATION ─── */
export function SleepGroupDurationForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <div className="p-4 bg-surface rounded-[12px]">
        <p className="text-sm font-semibold text-text-primary">목표</p>
        <p className="text-sm text-text-secondary mt-1">
          하루 7시간 이상 수면 — 매일 달성 여부를 기록합니다.
        </p>
      </div>
      <SleepGroupFooter form={form} onChange={onChange} />
    </div>
  );
}

/* ─── 그룹 WAKE_TIME ─── */
export function SleepGroupWakeForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <Chips
        label="목표 기상 시간"
        options={WAKE_TIME_OPTIONS}
        value={form.goal_config.wake_time}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, sleep_mode: "WAKE_TIME", wake_time: v },
          })
        }
      />
      <SleepGroupFooter form={form} onChange={onChange} />
    </div>
  );
}

/* ─── 그룹 GROUP_SUM (레거시, 미사용) ─── */
export function SleepGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  const sleepMode = form.goal_config.sleep_mode;

  return (
    <div className="space-y-6">
      <Step4Header />

      <RadioCards
        label="수면 목표 방식"
        options={GROUP_SLEEP_MODE_OPTIONS.map((o) => ({ ...o }))}
        value={sleepMode}
        onChange={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              sleep_mode: v as "BED_TIME" | "SLEEP_DURATION" | "WAKE_TIME",
            },
          })
        }
      />

      {/* BED_TIME 선택 시 시간대 추가 선택 */}
      {sleepMode === "BED_TIME" && (
        <Chips
          label="목표 취침 시간대"
          options={BED_TIME_OPTIONS}
          value={form.goal_config.sleep_time_range}
          onChange={(v) =>
            onChange({
              goal_config: { ...form.goal_config, sleep_time_range: v },
            })
          }
        />
      )}

      {/* WAKE_TIME 선택 시 기상 시간 추가 선택 */}
      {sleepMode === "WAKE_TIME" && (
        <Chips
          label="목표 기상 시간"
          options={WAKE_TIME_OPTIONS}
          value={form.goal_config.wake_time}
          onChange={(v) =>
            onChange({
              goal_config: { ...form.goal_config, wake_time: v },
            })
          }
        />
      )}

      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, group_target_count: v } })
        }
      />
      <WeeklyDurationNote />
      <MaxParticipantsSlider
        value={form.max_participants}
        onChange={(v) => onChange({ max_participants: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup />
    </div>
  );
}
