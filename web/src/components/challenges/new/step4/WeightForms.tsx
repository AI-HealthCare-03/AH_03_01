"use client";

import { useState } from "react";
import {
  RadioCards,
  TitleInput,
  MaxParticipantsChips,
  RewardPreview,
  Step4Header,
  Chips,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   체중 관리 Step4 폼
   카테고리는 DIET + kind="WEIGHT" 로 처리
   - WeightPersonalForm (개인 DAILY)
   - WeightGroupForm    (그룹 GROUP_MEMBERS)

   알려진 한계: 백엔드 category enum에 WEIGHT_MANAGEMENT가 없어
   DIET + goal_config.kind="WEIGHT" 로 우회함.
   ========================================= */

const DURATION_WEIGHT_OPTIONS = [
  { value: 30, label: "1개월" },
  { value: 90, label: "3개월" },
  { value: 180, label: "6개월" },
] as const;

const WEIGHT_MODE_OPTIONS = [
  {
    value: "MAINTAIN",
    emoji: "⚖️",
    title: "체중 유지",
    desc: "현재 체중을 유지하는 것이 목표",
  },
  {
    value: "PERCENT_5",
    emoji: "📉",
    title: "5% 감량",
    desc: "현재 체중의 5% 줄이기",
  },
  {
    value: "USER_INPUT",
    emoji: "✏️",
    title: "직접 설정",
    desc: "감량 목표 kg을 직접 입력",
  },
] as const;

/* ─── 개인 ─── */
export function WeightPersonalForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  const weightMode = form.goal_config.weight_loss_mode;
  const [customKg, setCustomKg] = useState<string>(
    form.goal_config.weight_loss_kg?.toString() ?? ""
  );

  return (
    <div className="space-y-6">
      <Step4Header />

      {/* 기간 선택 */}
      <div>
        <label className="block text-sm font-semibold text-text-primary mb-2">
          챌린지 기간
        </label>
        <div className="flex gap-2">
          {DURATION_WEIGHT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange({ duration_days: opt.value as 7 | 14 | 30 })}
              className={[
                "flex-1 py-2.5 rounded-[10px] text-sm font-semibold border-2 transition-all",
                form.duration_days === opt.value
                  ? "border-brand-black bg-brand text-brand-black"
                  : "border-border bg-white text-text-secondary hover:border-brand",
              ].join(" ")}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 목표 모드 */}
      <RadioCards
        label="감량 목표"
        options={WEIGHT_MODE_OPTIONS.map((o) => ({ ...o }))}
        value={weightMode}
        onChange={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              kind: "WEIGHT",
              weight_loss_mode: v as "MAINTAIN" | "PERCENT_5" | "USER_INPUT",
              weight_loss_kg: v !== "USER_INPUT" ? undefined : form.goal_config.weight_loss_kg,
            },
          })
        }
      />

      {/* 직접 입력 */}
      {weightMode === "USER_INPUT" && (
        <div>
          <label
            htmlFor="weight-kg"
            className="block text-sm font-semibold text-text-primary mb-2"
          >
            감량 목표 (kg)
          </label>
          <input
            id="weight-kg"
            type="number"
            min={0.5}
            max={50}
            step={0.5}
            value={customKg}
            onChange={(e) => {
              setCustomKg(e.target.value);
              const parsed = parseFloat(e.target.value);
              if (!isNaN(parsed) && parsed > 0) {
                onChange({
                  goal_config: { ...form.goal_config, weight_loss_kg: parsed },
                });
              }
            }}
            placeholder="예: 5"
            className="w-32 h-12 px-4 rounded-[12px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white text-center"
            aria-label="감량 목표 kg 입력"
          />
          <span className="ml-2 text-sm text-text-secondary">kg</span>
        </div>
      )}

      <div className="p-3 bg-surface rounded-[10px]">
        <p className="text-xs text-text-secondary">
          인증 방식: 매일 사진 인증 (식단 및 체중 기록 사진)
        </p>
      </div>

      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}

/* ─── 그룹 GROUP_MEMBERS ─── */
export function WeightGroupForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  const weightMode = form.goal_config.weight_loss_mode;
  const [customKg, setCustomKg] = useState<string>(
    form.goal_config.weight_loss_kg?.toString() ?? ""
  );

  return (
    <div className="space-y-6">
      <Step4Header />

      {/* 기간 */}
      <div>
        <label className="block text-sm font-semibold text-text-primary mb-2">
          챌린지 기간
        </label>
        <div className="flex gap-2">
          {DURATION_WEIGHT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange({ duration_days: opt.value as 7 | 14 | 30 })}
              className={[
                "flex-1 py-2.5 rounded-[10px] text-sm font-semibold border-2 transition-all",
                form.duration_days === opt.value
                  ? "border-brand-black bg-brand text-brand-black"
                  : "border-border bg-white text-text-secondary hover:border-brand",
              ].join(" ")}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 목표 모드 */}
      <RadioCards
        label="감량 목표"
        options={WEIGHT_MODE_OPTIONS.map((o) => ({ ...o }))}
        value={weightMode}
        onChange={(v) =>
          onChange({
            goal_config: {
              ...form.goal_config,
              kind: "WEIGHT",
              weight_loss_mode: v as "MAINTAIN" | "PERCENT_5" | "USER_INPUT",
            },
          })
        }
      />

      {weightMode === "USER_INPUT" && (
        <div>
          <label
            htmlFor="weight-kg-group"
            className="block text-sm font-semibold text-text-primary mb-2"
          >
            감량 목표 (kg)
          </label>
          <input
            id="weight-kg-group"
            type="number"
            min={0.5}
            max={50}
            step={0.5}
            value={customKg}
            onChange={(e) => {
              setCustomKg(e.target.value);
              const parsed = parseFloat(e.target.value);
              if (!isNaN(parsed) && parsed > 0) {
                onChange({
                  goal_config: { ...form.goal_config, weight_loss_kg: parsed },
                });
              }
            }}
            placeholder="예: 5"
            className="w-32 h-12 px-4 rounded-[12px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white text-center"
          />
          <span className="ml-2 text-sm text-text-secondary">kg</span>
        </div>
      )}

      {/* 달성 인원 */}
      <MaxParticipantsChips
        value={form.max_participants}
        onChange={(v) => onChange({
          max_participants: v,
          goal_config: { ...form.goal_config, group_target_members: v },
        })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup />
    </div>
  );
}
