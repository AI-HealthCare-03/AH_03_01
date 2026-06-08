"use client";

import type { WizardFormState } from "@/types/challenge";
/* Water */
import {
  WaterDailyForm,
  WaterWeeklyForm,
  WaterGroupForm,
} from "./step4/WaterForms";
/* Sleep */
import {
  SleepBedTimeForm,
  SleepDurationForm,
  SleepWakeForm,
  SleepGroupBedTimeForm,
  SleepGroupDurationForm,
  SleepGroupWakeForm,
} from "./step4/SleepForms";
/* Diet */
import {
  DietAvoidForm,
  DietIncludeForm,
  DietGroupForm,
} from "./step4/DietForms";
/* Weight */
import { WeightPersonalForm, WeightGroupForm } from "./step4/WeightForms";
/* Disease */
import { DiseaseFootForm } from "./step4/DiseaseForms";
/* No Smoking / No Alcohol */
import {
  NoSmokingForm,
  NoSmokingWeeklyForm,
  NoSmokingGroupForm,
  NoAlcoholForm,
  NoAlcoholWeeklyForm,
  NoAlcoholGroupForm,
} from "./step4/NoSmokingAlcoholForms";
/* Meditation */
import {
  MeditationDailyForm,
  MeditationWeeklyForm,
  MeditationGroupForm,
} from "./step4/MeditationForms";
/* Exercise */
import {
  WalkingDailyForm,
  WalkingWeeklyForm,
  WalkingGroupForm,
  RunningDailyForm,
  RunningWeeklyForm,
  RunningGroupForm,
  CyclingWeeklyForm,
  CyclingGroupForm,
  StrengthDailyForm,
  StrengthWeeklyForm,
  StrengthGroupForm,
  SwimmingWeeklyForm,
  SwimmingGroupForm,
  OtherWeeklyForm,
  OtherGroupForm,
} from "./step4/ExerciseForms";

/* =========================================
   Step 4: 카테고리 / sub_category / step3Mode / scope
   를 기반으로 적절한 폼 컴포넌트를 렌더하는 라우터
   ========================================= */

interface WizardStep4Props {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}

export default function WizardStep4({ form, onChange }: WizardStep4Props) {
  const { category, sub_category, scope, step3Mode } = form;
  const isGroup = scope === "GROUP";

  /* ─── EXERCISE ─── */
  if (category === "EXERCISE") {
    if (isGroup) {
      switch (sub_category) {
        case "WALKING":  return <WalkingGroupForm form={form} onChange={onChange} />;
        case "RUNNING":  return <RunningGroupForm form={form} onChange={onChange} />;
        case "CYCLING":  return <CyclingGroupForm form={form} onChange={onChange} />;
        case "STRENGTH": return <StrengthGroupForm form={form} onChange={onChange} />;
        case "SWIMMING": return <SwimmingGroupForm form={form} onChange={onChange} />;
        case "OTHER":    return <OtherGroupForm form={form} onChange={onChange} />;
      }
    }
    /* 개인 — step3Mode 에 "WEEKLY_COUNT" 이면 주간횟수형 (CYCLING/SWIMMING은 WEEKLY_COUNT만) */
    const isWeekly = step3Mode === "WEEKLY_COUNT";
    switch (sub_category) {
      case "WALKING":
        return isWeekly
          ? <WalkingWeeklyForm form={form} onChange={onChange} />
          : <WalkingDailyForm form={form} onChange={onChange} />;
      case "RUNNING":
        return isWeekly
          ? <RunningWeeklyForm form={form} onChange={onChange} />
          : <RunningDailyForm form={form} onChange={onChange} />;
      case "CYCLING":
        return <CyclingWeeklyForm form={form} onChange={onChange} />;
      case "STRENGTH":
        return isWeekly
          ? <StrengthWeeklyForm form={form} onChange={onChange} />
          : <StrengthDailyForm form={form} onChange={onChange} />;
      case "SWIMMING":
        return <SwimmingWeeklyForm form={form} onChange={onChange} />;
      case "OTHER":
        return <OtherWeeklyForm form={form} onChange={onChange} />;
    }
  }

  /* ─── WATER ─── */
  if (category === "WATER") {
    if (isGroup) return <WaterGroupForm form={form} onChange={onChange} />;
    if (step3Mode === "WEEKLY_COUNT") return <WaterWeeklyForm form={form} onChange={onChange} />;
    return <WaterDailyForm form={form} onChange={onChange} />;
  }

  /* ─── SLEEP ─── */
  if (category === "SLEEP") {
    if (isGroup) {
      switch (step3Mode) {
        case "BED_TIME":       return <SleepGroupBedTimeForm form={form} onChange={onChange} />;
        case "SLEEP_DURATION": return <SleepGroupDurationForm form={form} onChange={onChange} />;
        case "WAKE_TIME":      return <SleepGroupWakeForm form={form} onChange={onChange} />;
      }
    }
    switch (step3Mode) {
      case "BED_TIME":       return <SleepBedTimeForm form={form} onChange={onChange} />;
      case "SLEEP_DURATION": return <SleepDurationForm form={form} onChange={onChange} />;
      case "WAKE_TIME":      return <SleepWakeForm form={form} onChange={onChange} />;
    }
  }

  /* ─── DIET ─── */
  if (category === "DIET") {
    if (isGroup) return <DietGroupForm form={form} onChange={onChange} />;
    if (step3Mode === "AVOID") return <DietAvoidForm form={form} onChange={onChange} />;
    if (step3Mode === "INCLUDE") return <DietIncludeForm form={form} onChange={onChange} />;
  }

  /* ─── WEIGHT_MANAGEMENT ─── */
  if (category === "WEIGHT_MANAGEMENT") {
    if (isGroup) return <WeightGroupForm form={form} onChange={onChange} />;
    return <WeightPersonalForm form={form} onChange={onChange} />;
  }

  /* ─── DISEASE_CARE ─── */
  if (category === "DISEASE_CARE") {
    /* step3Mode = questionnaire_template 이름 */
    return <DiseaseFootForm form={form} onChange={onChange} />;
  }

  /* ─── NO_SMOKING ─── */
  if (category === "NO_SMOKING") {
    if (isGroup) return <NoSmokingGroupForm form={form} onChange={onChange} />;
    if (step3Mode === "WEEKLY_COUNT") return <NoSmokingWeeklyForm form={form} onChange={onChange} />;
    return <NoSmokingForm form={form} onChange={onChange} />;
  }

  /* ─── NO_ALCOHOL ─── */
  if (category === "NO_ALCOHOL") {
    if (isGroup) return <NoAlcoholGroupForm form={form} onChange={onChange} />;
    if (step3Mode === "WEEKLY_COUNT") return <NoAlcoholWeeklyForm form={form} onChange={onChange} />;
    return <NoAlcoholForm form={form} onChange={onChange} />;
  }

  /* ─── MEDITATION ─── */
  if (category === "MEDITATION") {
    if (isGroup) return <MeditationGroupForm form={form} onChange={onChange} />;
    if (step3Mode === "WEEKLY_COUNT") return <MeditationWeeklyForm form={form} onChange={onChange} />;
    return <MeditationDailyForm form={form} onChange={onChange} />;
  }

  /* 폴백 */
  return (
    <div className="p-6 text-center text-text-secondary">
      카테고리를 선택해 주세요.
    </div>
  );
}
