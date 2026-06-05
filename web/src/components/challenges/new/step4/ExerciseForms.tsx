"use client";

import { useState } from "react";
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
  WEEKLY_COUNT_OPTIONS,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   EXERCISE 카테고리 Step4 폼 — sub_category 별
   각 운동에서 공통 pattern을 prop으로 추상화하고
   sub별 선택지만 다르게 주입.
   ========================================= */

/* ─── 시간 옵션 공통 ─── */
const TIME_30_60_90_120 = [
  { value: 30, label: "30분" },
  { value: 60, label: "60분" },
  { value: 90, label: "90분" },
  { value: 120, label: "120분" },
];

const TIME_20_30_40_60 = [
  { value: 20, label: "20분" },
  { value: 30, label: "30분" },
  { value: 40, label: "40분" },
  { value: 60, label: "60분" },
];

/* ─── 걷기 ─── */
const WALKING_DISTANCE_OPTIONS = [
  { value: 3, label: "3 km" },
  { value: 5, label: "5 km" },
  { value: 7, label: "7 km" },
];

const WALKING_STEP_OPTIONS = [
  { value: 5000, label: "5,000보" },
  { value: 7000, label: "7,000보" },
  { value: 10000, label: "10,000보" },
];

/* 걷기 목표 모드 라디오 */
type WalkingGoalMode = "TIME" | "DISTANCE" | "STEPS";

function initWalkingMode(form: WizardFormState): WalkingGoalMode {
  if (form.goal_config.distance_km !== undefined) return "DISTANCE";
  if (form.goal_config.step_count !== undefined) return "STEPS";
  return "TIME";
}

function WalkingGoalPicker({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  // goal_config 파생이 아닌 로컬 state로 모드 관리 (파생 시 undefined → 모드 고정 버그 방지)
  const [mode, setMode] = useState<WalkingGoalMode>(() =>
    initWalkingMode(form),
  );

  const handleModeChange = (newMode: WalkingGoalMode) => {
    setMode(newMode);
    onChange({
      goal_type:
        newMode === "TIME"
          ? "DURATION"
          : newMode === "DISTANCE"
            ? "AMOUNT"
            : "COUNT",
      goal_config: {
        ...form.goal_config,
        duration_minutes:
          newMode === "TIME" ? form.goal_config.duration_minutes : undefined,
        distance_km:
          newMode === "DISTANCE" ? form.goal_config.distance_km : undefined,
        step_count:
          newMode === "STEPS" ? form.goal_config.step_count : undefined,
      },
    });
  };

  return (
    <>
      <RadioCards
        label="목표 방식"
        options={[
          {
            value: "TIME" as WalkingGoalMode,
            emoji: "⏱️",
            title: "시간",
            desc: "분 단위 목표",
          },
          {
            value: "DISTANCE" as WalkingGoalMode,
            emoji: "📍",
            title: "거리",
            desc: "km 단위 목표",
          },
          {
            value: "STEPS" as WalkingGoalMode,
            emoji: "👣",
            title: "걸음 수",
            desc: "보 단위 목표",
          },
        ]}
        value={mode}
        onChange={handleModeChange}
      />
      {mode === "TIME" && (
        <Chips
          label="목표 시간"
          options={TIME_30_60_90_120}
          value={form.goal_config.duration_minutes}
          onChange={(v) =>
            onChange({
              goal_config: { ...form.goal_config, duration_minutes: v },
            })
          }
        />
      )}
      {mode === "DISTANCE" && (
        <Chips
          label="목표 거리"
          options={WALKING_DISTANCE_OPTIONS}
          value={form.goal_config.distance_km}
          onChange={(v) =>
            onChange({ goal_config: { ...form.goal_config, distance_km: v } })
          }
        />
      )}
      {mode === "STEPS" && (
        <Chips
          label="목표 걸음 수"
          options={WALKING_STEP_OPTIONS}
          value={form.goal_config.step_count}
          onChange={(v) =>
            onChange({ goal_config: { ...form.goal_config, step_count: v } })
          }
        />
      )}
    </>
  );
}

/* WALKING DAILY */
export function WalkingDailyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <WalkingGoalPicker form={form} onChange={onChange} />
      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

/* WALKING WEEKLY */
export function WalkingWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <WalkingGoalPicker form={form} onChange={onChange} />
      <Chips
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, weekly_target_count: v },
          })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

export function WalkingGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <WalkingGoalPicker form={form} onChange={onChange} />
      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, group_target_count: v },
          })
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

/* ─── 러닝 ─── */
const RUNNING_DISTANCE_OPTIONS = [
  { value: 3, label: "3 km" },
  { value: 5, label: "5 km" },
  { value: 8, label: "8 km" },
  { value: 10, label: "10 km" },
];

const RUNNING_GROUP_DISTANCE = [
  { value: 3, label: "3 km" },
  { value: 5, label: "5 km" },
  { value: 7, label: "7 km" },
];

type RunningGoalMode = "TIME" | "DISTANCE";

function initRunningMode(form: WizardFormState): RunningGoalMode {
  if (form.goal_config.distance_km !== undefined) return "DISTANCE";
  return "TIME";
}

function RunningGoalPicker({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  // goal_config 파생이 아닌 로컬 state로 모드 관리 (파생 시 undefined → 모드 고정 버그 방지)
  const [mode, setMode] = useState<RunningGoalMode>(() =>
    initRunningMode(form),
  );

  const handleModeChange = (newMode: RunningGoalMode) => {
    setMode(newMode);
    onChange({
      goal_type: newMode === "TIME" ? "DURATION" : "AMOUNT",
      goal_config: {
        ...form.goal_config,
        duration_minutes:
          newMode === "TIME" ? form.goal_config.duration_minutes : undefined,
        distance_km:
          newMode === "DISTANCE" ? form.goal_config.distance_km : undefined,
      },
    });
  };

  return (
    <>
      <RadioCards
        label="목표 방식"
        options={[
          {
            value: "TIME" as RunningGoalMode,
            emoji: "⏱️",
            title: "시간",
            desc: "분 단위 목표",
          },
          {
            value: "DISTANCE" as RunningGoalMode,
            emoji: "📍",
            title: "거리",
            desc: "km 단위 목표",
          },
        ]}
        value={mode}
        onChange={handleModeChange}
      />
      {mode === "TIME" && (
        <Chips
          label="목표 시간"
          options={TIME_30_60_90_120}
          value={form.goal_config.duration_minutes}
          onChange={(v) =>
            onChange({
              goal_config: { ...form.goal_config, duration_minutes: v },
            })
          }
        />
      )}
      {mode === "DISTANCE" && (
        <Chips
          label="목표 거리"
          options={RUNNING_DISTANCE_OPTIONS}
          value={form.goal_config.distance_km}
          onChange={(v) =>
            onChange({ goal_config: { ...form.goal_config, distance_km: v } })
          }
        />
      )}
    </>
  );
}

export function RunningDailyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <RunningGoalPicker form={form} onChange={onChange} />
      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

export function RunningWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <RunningGoalPicker form={form} onChange={onChange} />
      <Chips
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, weekly_target_count: v },
          })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

export function RunningGroupForm({
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
        label="그룹 목표 거리"
        options={RUNNING_GROUP_DISTANCE}
        value={form.goal_config.distance_km}
        onChange={(v) =>
          onChange({ goal_config: { ...form.goal_config, distance_km: v } })
        }
      />
      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, group_target_count: v },
          })
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

/* ─── 자전거 (CYCLING) — 개인 WEEKLY_COUNT + 그룹 GROUP_SUM ─── */
export function CyclingWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <div className="p-3 bg-surface rounded-[10px]">
        <p className="text-xs text-text-secondary">
          1일 1회만 횟수로 인정됩니다.
        </p>
      </div>
      <Chips
        label="목표 시간"
        options={TIME_30_60_90_120}
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, duration_minutes: v },
          })
        }
      />
      <Chips
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, weekly_target_count: v },
          })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

export function CyclingGroupForm({
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
        label="목표 시간"
        options={TIME_30_60_90_120}
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, duration_minutes: v },
          })
        }
      />
      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, group_target_count: v },
          })
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

/* ─── 근력 (STRENGTH) ─── */
export function StrengthDailyForm({
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
        label="목표 시간"
        options={TIME_20_30_40_60}
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, duration_minutes: v },
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

export function StrengthWeeklyForm({
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
        label="목표 시간"
        options={TIME_20_30_40_60}
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, duration_minutes: v },
          })
        }
      />
      <Chips
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, weekly_target_count: v },
          })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

export function StrengthGroupForm({
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
        label="목표 시간"
        options={TIME_20_30_40_60}
        value={form.goal_config.duration_minutes}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, duration_minutes: v },
          })
        }
      />
      <Chips
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, group_target_count: v },
          })
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

/* ─── 수영 (SWIMMING) — 개인 WEEKLY_COUNT + 그룹 GROUP_SUM ─── */
export function SwimmingWeeklyForm({
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
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, weekly_target_count: v },
          })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

export function SwimmingGroupForm({
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
        label="그룹 합산 목표 횟수"
        options={GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, group_target_count: v },
          })
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

/* ─── 기타 운동 (OTHER) ─── */
const OTHER_EXERCISE_TYPES = [
  "등산",
  "요가",
  "필라테스",
  "홈트레이닝",
  "배드민턴",
  "테니스",
  "축구",
  "농구",
  "기타",
];

const OTHER_GROUP_SUM_OPTIONS = [
  { value: 3, label: "3회" },
  { value: 5, label: "5회" },
  { value: 7, label: "7회" },
  { value: 10, label: "10회" },
];

function OtherTypePicker({
  value,
  onChange,
}: {
  value: string | undefined;
  onChange: (v: string) => void;
}) {
  const [customVal, setCustomVal] = useState(
    value && !OTHER_EXERCISE_TYPES.slice(0, -1).includes(value) ? value : "",
  );

  return (
    <div>
      <label className="block text-sm font-semibold text-text-primary mb-2">
        운동 종류
      </label>
      <div className="flex flex-wrap gap-2 mb-3">
        {OTHER_EXERCISE_TYPES.map((t) => {
          const isCustom = t === "기타";
          const isSelected = isCustom
            ? value !== undefined &&
              !OTHER_EXERCISE_TYPES.slice(0, -1).includes(value)
            : value === t;
          return (
            <button
              key={t}
              type="button"
              onClick={() => {
                if (!isCustom) onChange(t);
              }}
              className={[
                "px-3 py-1.5 rounded-full text-xs font-medium border-2 transition-all",
                isSelected
                  ? "border-brand-black bg-brand text-brand-black"
                  : "border-border bg-white text-text-secondary hover:border-brand",
              ].join(" ")}
            >
              {t}
            </button>
          );
        })}
      </div>

      {/* 기타 직접 입력 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={customVal}
          onChange={(e) => {
            setCustomVal(e.target.value);
            if (e.target.value.trim()) onChange(e.target.value.trim());
          }}
          placeholder="직접 입력 (예: 클라이밍)"
          className="flex-1 h-10 px-3 rounded-[10px] border border-border text-sm focus:outline-none focus:border-brand-black"
        />
      </div>
    </div>
  );
}

export function OtherWeeklyForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <OtherTypePicker
        value={form.goal_config.exercise_other_type}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, exercise_other_type: v },
          })
        }
      />
      <Chips
        label="주간 목표 횟수"
        options={WEEKLY_COUNT_OPTIONS}
        value={form.goal_config.weekly_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, weekly_target_count: v },
          })
        }
      />
      <WeeklyDurationNote />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup={false} />
    </div>
  );
}

export function OtherGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />
      <OtherTypePicker
        value={form.goal_config.exercise_other_type}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, exercise_other_type: v },
          })
        }
      />
      <Chips
        label="그룹 합산 목표 횟수"
        options={OTHER_GROUP_SUM_OPTIONS}
        value={form.goal_config.group_target_count}
        onChange={(v) =>
          onChange({
            goal_config: { ...form.goal_config, group_target_count: v },
          })
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
