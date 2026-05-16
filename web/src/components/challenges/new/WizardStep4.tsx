"use client";

import { useEffect } from "react";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type {
  WizardFormState,
  GoalType,
  ChallengeCategory,
  ExerciseSubType,
} from "@/types/challenge";

/* =========================================
   Step 4: 목표 설정 + 보상 미리보기
   ========================================= */

interface WizardStep4Props {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}

/* 카테고리별 자동 goal_type 기본값 */
const CATEGORY_DEFAULT_GOAL: Record<ChallengeCategory, GoalType> = {
  EXERCISE: "DURATION",
  WATER: "AMOUNT",
  SLEEP: "DURATION",
  DIET: "CHECK",
  NO_SMOKING: "CHECK",
  NO_ALCOHOL: "CHECK",
  DISEASE_CARE: "CHECK",
  MEDITATION: "DURATION",
};

/* EXERCISE sub 별 goal 옵션 */
const EXERCISE_GOAL_OPTIONS: Record<
  ExerciseSubType,
  { label: string; type: GoalType; chips: { value: number; label: string }[] }[]
> = {
  WALKING: [
    { label: "걸음수", type: "COUNT", chips: [{ value: 5000, label: "5,000보" }, { value: 8000, label: "8,000보" }, { value: 10000, label: "10,000보" }] },
    { label: "거리 (km)", type: "AMOUNT", chips: [{ value: 3, label: "3km" }, { value: 5, label: "5km" }, { value: 10, label: "10km" }] },
  ],
  RUNNING: [
    { label: "거리 (km)", type: "AMOUNT", chips: [{ value: 3, label: "3km" }, { value: 5, label: "5km" }, { value: 10, label: "10km" }] },
    { label: "시간 (분)", type: "DURATION", chips: [{ value: 20, label: "20분" }, { value: 30, label: "30분" }, { value: 60, label: "1시간" }] },
  ],
  STRENGTH: [
    { label: "시간 (분)", type: "DURATION", chips: [{ value: 30, label: "30분" }, { value: 45, label: "45분" }, { value: 60, label: "1시간" }] },
  ],
  CYCLING: [
    { label: "거리 (km)", type: "AMOUNT", chips: [{ value: 10, label: "10km" }, { value: 20, label: "20km" }, { value: 30, label: "30km" }] },
    { label: "시간 (분)", type: "DURATION", chips: [{ value: 30, label: "30분" }, { value: 45, label: "45분" }, { value: 60, label: "1시간" }] },
  ],
  SWIMMING: [
    { label: "시간 (분)", type: "DURATION", chips: [{ value: 30, label: "30분" }, { value: 45, label: "45분" }, { value: 60, label: "1시간" }] },
  ],
  OTHER: [
    { label: "시간 (분)", type: "DURATION", chips: [{ value: 20, label: "20분" }, { value: 30, label: "30분" }, { value: 60, label: "1시간" }] },
  ],
};

/* 카테고리별 일반 goal 옵션 */
const GENERAL_GOAL_OPTIONS: Partial<
  Record<
    ChallengeCategory,
    { label: string; chips: { value: number; label: string }[] }
  >
> = {
  WATER: { label: "하루 마실 양 (ml)", chips: [{ value: 500, label: "500ml" }, { value: 1000, label: "1L" }, { value: 1500, label: "1.5L" }, { value: 2000, label: "2L" }] },
  SLEEP: { label: "목표 수면 시간 (시간)", chips: [{ value: 6, label: "6시간" }, { value: 7, label: "7시간" }, { value: 8, label: "8시간" }] },
  MEDITATION: { label: "명상 시간 (분)", chips: [{ value: 5, label: "5분" }, { value: 10, label: "10분" }, { value: 20, label: "20분" }] },
};

const DURATION_OPTIONS: { value: 7 | 14 | 30; label: string }[] = [
  { value: 7, label: "7일" },
  { value: 14, label: "14일" },
  { value: 30, label: "한 달" },
];

/* 기본 챌린지 제목 자동 생성 */
function buildDefaultTitle(form: WizardFormState): string {
  if (!form.category) return "";
  const cat = CATEGORY_CONFIG[form.category];
  const sub =
    form.sub_category
      ? EXERCISE_GOAL_OPTIONS[form.sub_category]?.[0]?.label ?? ""
      : "";
  const scopeLabel = form.scope === "GROUP" ? "그룹 " : "";
  const subLabel = sub ? ` (${sub})` : "";
  return `${scopeLabel}${cat.label} 챌린지${subLabel}`;
}

export default function WizardStep4({ form, onChange }: WizardStep4Props) {
  /* 카테고리 변경 시 goal_type 자동 설정 */
  useEffect(() => {
    if (form.category && form.category !== "EXERCISE") {
      onChange({ goal_type: CATEGORY_DEFAULT_GOAL[form.category] });
    }
  }, [form.category]); // eslint-disable-line react-hooks/exhaustive-deps

  /* 제목 자동 채우기 */
  useEffect(() => {
    const defaultTitle = buildDefaultTitle(form);
    if (!form.title && defaultTitle) {
      onChange({ title: defaultTitle });
    }
  }, [form.category, form.sub_category, form.scope]); // eslint-disable-line react-hooks/exhaustive-deps

  const isExercise = form.category === "EXERCISE";
  const goalOptions = isExercise && form.sub_category
    ? EXERCISE_GOAL_OPTIONS[form.sub_category] ?? []
    : [];
  const generalOpt = form.category ? GENERAL_GOAL_OPTIONS[form.category] : null;
  const showChips = isExercise
    ? goalOptions.length > 0
    : !!generalOpt;
  const chips = isExercise && goalOptions.length > 0
    ? goalOptions[0].chips
    : (generalOpt?.chips ?? []);
  const chipsLabel = isExercise && goalOptions.length > 0
    ? goalOptions[0].label
    : (generalOpt?.label ?? "목표 값");

  const estimatedDaily = 70;
  const totalEstimated = estimatedDaily * form.duration_days + 200;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-text-primary mb-1">목표 설정</h2>
        <p className="text-sm text-text-secondary">
          구체적인 목표를 설정하면 달성하기 쉬워요
        </p>
      </div>

      {/* 목표 값 칩 선택 */}
      {showChips && (
        <div>
          <label className="block text-sm font-semibold text-text-primary mb-2">
            {chipsLabel}
          </label>
          <div className="flex flex-wrap gap-2">
            {chips.map((chip) => (
              <button
                key={chip.value}
                type="button"
                onClick={() => onChange({ goal_value: chip.value })}
                className={[
                  "px-4 py-2 rounded-full text-sm font-medium border-2 transition-all",
                  form.goal_value === chip.value
                    ? "border-brand-black bg-brand text-brand-black"
                    : "border-border bg-white text-text-secondary hover:border-brand",
                ].join(" ")}
              >
                {chip.label}
              </button>
            ))}
            {/* 직접 입력 */}
            <input
              type="number"
              min={1}
              value={form.goal_value || ""}
              onChange={(e) =>
                onChange({ goal_value: parseFloat(e.target.value) || 0 })
              }
              placeholder="직접 입력"
              className="w-24 h-10 px-3 rounded-full border-2 border-border text-sm text-center focus:outline-none focus:border-brand-black"
              aria-label="목표값 직접 입력"
            />
          </div>
        </div>
      )}

      {/* 체크형 카테고리 - 별도 수치 없음 */}
      {!showChips && (
        <div className="p-4 bg-surface rounded-[12px]">
          <p className="text-sm text-text-secondary">
            이 챌린지는 매일 체크로 인증해요. 달성 여부만 기록됩니다.
          </p>
        </div>
      )}

      {/* 기간 선택 */}
      <div>
        <label className="block text-sm font-semibold text-text-primary mb-2">
          챌린지 기간
        </label>
        <div className="flex gap-2">
          {DURATION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange({ duration_days: opt.value })}
              className={[
                "flex-1 py-2 rounded-[10px] text-sm font-semibold border-2 transition-all",
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

      {/* 챌린지 이름 */}
      <div>
        <label
          htmlFor="challenge-title"
          className="block text-sm font-semibold text-text-primary mb-2"
        >
          챌린지 이름
        </label>
        <input
          id="challenge-title"
          type="text"
          value={form.title}
          onChange={(e) => onChange({ title: e.target.value })}
          maxLength={40}
          className="w-full h-12 px-4 rounded-[12px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white"
          placeholder="챌린지 이름을 입력하세요"
        />
        <p className="text-xs text-text-tertiary mt-1 text-right">
          {form.title.length}/40
        </p>
      </div>

      {/* 그룹 전용: 최대 참여 인원 슬라이더 */}
      {form.scope === "GROUP" && (
        <div>
          <label
            htmlFor="max-participants"
            className="block text-sm font-semibold text-text-primary mb-2"
          >
            최대 참여 인원{" "}
            <span className="font-bold text-brand-black">
              {form.max_participants}명
            </span>
          </label>
          <input
            id="max-participants"
            type="range"
            min={2}
            max={5}
            value={form.max_participants}
            onChange={(e) =>
              onChange({ max_participants: parseInt(e.target.value) })
            }
            className="w-full accent-brand-black"
            aria-label={`최대 참여 인원 ${form.max_participants}명`}
          />
          <div className="flex justify-between text-xs text-text-tertiary mt-1">
            <span>2명</span>
            <span>5명</span>
          </div>
        </div>
      )}

      {/* 예상 보상 카드 (정적) */}
      <div className="rounded-[14px] border border-brand bg-brand/10 p-4">
        <p className="text-sm font-bold text-brand-black mb-3">
          예상 보상 미리보기
        </p>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">
              데일리 인증 × {form.duration_days}일
            </span>
            <span className="font-semibold">
              최대 {estimatedDaily * form.duration_days}P
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">기간 완주 보너스</span>
            <span className="font-semibold">200P</span>
          </div>
          {form.scope === "GROUP" && (
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">그룹 전체 완주 보너스</span>
              <span className="font-semibold">500P</span>
            </div>
          )}
          <div className="border-t border-brand/30 pt-2 flex justify-between text-sm font-bold">
            <span>최대 획득 예상</span>
            <span className="text-brand-black">
              {totalEstimated +
                (form.scope === "GROUP" ? 500 : 0)}
              P
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
