"use client";

import { useState } from "react";
import {
  Chips,
  DurationPicker,
  WeeklyDurationNote,
  TitleInput,
  MaxParticipantsChips,
  RewardPreview,
  Step4Header,
  GROUP_SUM_OPTIONS,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   DIET 카테고리 Step4 폼
   - DietAvoidForm    (개인 AVOID DAILY)
   - DietIncludeForm  (개인 INCLUDE DAILY)
   - DietGroupForm    (그룹 GROUP_SUM — 식단 종류 이미 Step3에서 선택됨)
   ========================================= */

/* 회피 음식 프리셋 */
const AVOID_PRESETS = [
  "기름진 음식",
  "패스트푸드",
  "라면",
  "과자/스낵",
  "탄산음료",
  "배달음식",
];

/* 포함 음식 프리셋 */
const INCLUDE_PRESETS = ["채소", "과일", "콩류", "생선", "견과류", "통곡물"];

/* ─── 음식 태그 입력 공통 ─── */
function FoodTagInput({
  label,
  presets,
  targets,
  onAdd,
  onRemove,
}: {
  label: string;
  presets: string[];
  targets: string[];
  onAdd: (v: string) => void;
  onRemove: (v: string) => void;
}) {
  const [inputVal, setInputVal] = useState("");

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (trimmed && !targets.includes(trimmed)) {
      onAdd(trimmed);
    }
    setInputVal("");
  };

  return (
    <div>
      <label className="block text-sm font-semibold text-text-primary mb-2">
        {label}
      </label>

      {/* 프리셋 버튼 */}
      <div className="flex flex-wrap gap-2 mb-3">
        {presets.map((p) => {
          const isSelected = targets.includes(p);
          return (
            <button
              key={p}
              type="button"
              onClick={() => (isSelected ? onRemove(p) : onAdd(p))}
              className={[
                "px-3 py-1.5 rounded-full text-xs font-medium border-2 transition-all",
                isSelected
                  ? "border-brand-black bg-brand text-brand-black"
                  : "border-border bg-white text-text-secondary hover:border-brand",
              ].join(" ")}
            >
              {isSelected ? "✓ " : "+ "}
              {p}
            </button>
          );
        })}
      </div>

      {/* 선택된 태그 */}
      {targets.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {targets.map((t) => (
            <span
              key={t}
              className="flex items-center gap-1 px-3 py-1 bg-brand/10 border border-brand rounded-full text-xs font-medium text-brand-black"
            >
              {t}
              <button
                type="button"
                onClick={() => onRemove(t)}
                className="ml-0.5 text-text-tertiary hover:text-red-500"
                aria-label={`${t} 제거`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* 직접 입력 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag(inputVal);
            }
          }}
          placeholder="직접 입력 후 Enter"
          className="flex-1 h-10 px-3 rounded-[10px] border border-border text-sm focus:outline-none focus:border-brand-black"
        />
        <button
          type="button"
          onClick={() => addTag(inputVal)}
          className="px-4 h-10 rounded-[10px] bg-brand-black text-white text-sm font-medium"
        >
          추가
        </button>
      </div>
    </div>
  );
}

/* ─── 개인 AVOID ─── */
export function DietAvoidForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  const targets = form.goal_config.diet_targets ?? [];

  return (
    <div className="space-y-6">
      <Step4Header />
      <FoodTagInput
        label="피할 음식 선택"
        presets={AVOID_PRESETS}
        targets={targets}
        onAdd={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              diet_mode: "AVOID",
              diet_targets: [...targets, v],
            },
          })
        }
        onRemove={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              diet_targets: targets.filter((t) => t !== v),
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

/* ─── 개인 INCLUDE ─── */
export function DietIncludeForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  const targets = form.goal_config.diet_targets ?? [];

  return (
    <div className="space-y-6">
      <Step4Header />
      <FoodTagInput
        label="먹을 음식 선택"
        presets={INCLUDE_PRESETS}
        targets={targets}
        onAdd={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              diet_mode: "INCLUDE",
              diet_targets: [...targets, v],
            },
          })
        }
        onRemove={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              diet_targets: targets.filter((t) => t !== v),
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

/* ─── 그룹 GROUP_SUM (식단 종류는 Step3에서 이미 선택됨) ─── */
const DIET_TYPE_LABELS: Record<string, string> = {
  MEDITERRANEAN: "지중해식",
  LOW_CARB: "저탄수",
  LOW_FAT: "저지방",
  LOW_SODIUM: "저염",
  LOW_SUGAR: "저당",
};

export function DietGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  const dietType = form.goal_config.diet_type;
  const dietLabel = dietType ? DIET_TYPE_LABELS[dietType] ?? dietType : "—";

  return (
    <div className="space-y-6">
      <Step4Header />

      {/* 선택된 식단 종류 표시 */}
      {dietType && (
        <div className="p-3 bg-surface rounded-[12px]">
          <p className="text-xs text-text-tertiary">선택된 식단</p>
          <p className="text-sm font-semibold text-text-primary mt-0.5">
            {dietLabel}
          </p>
        </div>
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
      <MaxParticipantsChips
        value={form.max_participants}
        onChange={(v) => onChange({ max_participants: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={7} isGroup />
    </div>
  );
}
