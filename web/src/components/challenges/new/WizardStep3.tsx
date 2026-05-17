"use client";

import ExerciseSubStep from "./step3/ExerciseSubStep";
import DailyOrWeeklyStep from "./step3/DailyOrWeeklyStep";
import SleepModeStep from "./step3/SleepModeStep";
import DietModeStep from "./step3/DietModeStep";
import DiseaseTypeStep from "./step3/DiseaseTypeStep";
import type { WizardFormState, ExerciseSubType } from "@/types/challenge";

/* =========================================
   Step 3: 카테고리별 세부 분기 라우터
   - EXERCISE    → 운동 종류 (WALKING / RUNNING / ...)
   - SLEEP       → 수면 모드 (BED_TIME / SLEEP_DURATION / WAKE_TIME)
   - DIET        → 식단 모드 (AVOID / INCLUDE / WEIGHT, 그룹은 식단종류)
   - DISEASE_CARE → 질환 종류
   - WATER / MEDITATION / NO_SMOKING / NO_ALCOHOL → 매일 vs 주간횟수
   - 그룹 WATER / MEDITATION → 자동 GROUP_SUM, step3Mode="GROUP_AUTO"
   - 그룹 NO_SMOKING / NO_ALCOHOL → 자동 GROUP_MEMBERS, step3Mode="GROUP_AUTO"
   ========================================= */

interface WizardStep3Props {
  form: WizardFormState;
  onExerciseSub: (sub: ExerciseSubType) => void;
  onStep3Mode: (mode: string) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  WATER: "물 마시기",
  MEDITATION: "명상",
  NO_SMOKING: "금연",
  NO_ALCOHOL: "금주",
};

export default function WizardStep3({
  form,
  onExerciseSub,
  onStep3Mode,
}: WizardStep3Props) {
  const { category, sub_category, scope, step3Mode } = form;

  /* 그룹 + (WATER/MEDITATION/NO_SMOKING/NO_ALCOHOL/DISEASE_CARE) → step3 건너뜀 안내
     실제로는 page.tsx 에서 자동으로 넘기지만, 혹시 렌더될 경우 대비 */
  if (!category) return null;

  /* EXERCISE → 운동 종류 선택 */
  if (category === "EXERCISE") {
    return (
      <ExerciseSubStep value={sub_category} onChange={onExerciseSub} />
    );
  }

  /* SLEEP → 수면 모드 선택 */
  if (category === "SLEEP") {
    return (
      <SleepModeStep
        value={step3Mode as "BED_TIME" | "SLEEP_DURATION" | "WAKE_TIME" | null}
        onChange={onStep3Mode}
      />
    );
  }

  /* DIET → 식단 모드 선택 */
  if (category === "DIET") {
    return (
      <DietModeStep
        scope={scope}
        value={step3Mode}
        onChange={onStep3Mode}
      />
    );
  }

  /* DISEASE_CARE → 질환 종류 선택 */
  if (category === "DISEASE_CARE") {
    return (
      <DiseaseTypeStep value={step3Mode} onChange={onStep3Mode} />
    );
  }

  /* WATER / MEDITATION / NO_SMOKING / NO_ALCOHOL — 개인만 도달 (그룹은 자동 건너뜀) */
  const catLabel = CATEGORY_LABELS[category] ?? category;
  return (
    <DailyOrWeeklyStep
      categoryLabel={catLabel}
      value={step3Mode as "DAILY" | "WEEKLY_COUNT" | null}
      onChange={onStep3Mode}
    />
  );
}
