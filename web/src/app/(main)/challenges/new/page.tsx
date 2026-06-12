"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import WizardShell from "@/components/challenges/new/WizardShell";
import WizardStep1 from "@/components/challenges/new/WizardStep1";
import WizardStep2 from "@/components/challenges/new/WizardStep2";
import WizardStep3 from "@/components/challenges/new/WizardStep3";
import WizardStep4 from "@/components/challenges/new/WizardStep4";
import { useCreateChallenge } from "@/hooks/queries/useCreateChallenge";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { format } from "@/lib/dateUtils";
import type {
  WizardFormState,
  ChallengeScope,
  ChallengeVisibility,
  ChallengeCategory,
  ExerciseSubType,
  ChallengeCadence,
  GoalType,
} from "@/types/challenge";

/* =========================================
   챌린지 생성 4-Step 위저드
   Step1: 참여 방식 (개인/그룹)
   Step2: 카테고리 (8개)
   Step3: 카테고리별 세부 분기
   Step4: 목표 + 기간 + 미리보기 → 제출
   ========================================= */

/* ─── verification_type 자동 추론 ─── */
/* 사진으로 인증하기 어려운 카테고리는 체크 버튼 기반 인증을 사용한다.
   금주(NO_ALCOHOL) / 수면(SLEEP) / 질환 관리(DISEASE_CARE). */
function inferVerificationType(category: ChallengeCategory): "CHECK" | "PHOTO" {
  if (category === "NO_ALCOHOL") return "CHECK";
  if (category === "DISEASE_CARE") return "CHECK";
  if (category === "SLEEP") return "CHECK";
  return "PHOTO";
}

/* ─── cadence 자동 결정 ─── */
function inferCadence(
  scope: ChallengeScope,
  category: ChallengeCategory,
  step3Mode: string | null
): ChallengeCadence {
  if (scope === "GROUP") {
    /* GROUP_MEMBERS: NO_SMOKING / NO_ALCOHOL / WEIGHT_MANAGEMENT */
    if (
      category === "NO_SMOKING" ||
      category === "NO_ALCOHOL" ||
      category === "WEIGHT_MANAGEMENT"
    ) {
      return "GROUP_MEMBERS";
    }
    return "GROUP_SUM";
  }
  if (step3Mode === "WEEKLY_COUNT") return "WEEKLY_COUNT";
  return "DAILY";
}

/* ─── goal_type 자동 결정 ─── */
function inferGoalType(category: ChallengeCategory): GoalType {
  const checkTypes: ChallengeCategory[] = [
    "NO_SMOKING",
    "NO_ALCOHOL",
    "DISEASE_CARE",
    "DIET",
    "SLEEP",
  ];
  if (checkTypes.includes(category)) return "CHECK";
  if (category === "WATER") return "AMOUNT";
  if (category === "EXERCISE") return "DURATION";
  if (category === "MEDITATION") return "DURATION";
  return "CHECK";
}

/* ─── Step3 건너뜀 여부 판정 ─── */
function shouldSkipStep3(
  scope: ChallengeScope,
  category: ChallengeCategory
): boolean {
  /* 체중 관리는 개인/그룹 모두 step3 없이 step4로 바로 */
  if (category === "WEIGHT_MANAGEMENT") return true;
  /* 그룹 + 단순 카테고리는 step3 없이 step4로 바로 */
  if (scope === "GROUP") {
    /* DIET 그룹은 식단 종류를 step3에서 고름 → skip 안 함 */
    if (category === "DIET") return false;
    /* EXERCISE 그룹도 운동 종류를 step3에서 고름 → skip 안 함 */
    if (category === "EXERCISE") return false;
    /* SLEEP 그룹도 수면 모드를 step3에서 고름 → skip 안 함 */
    if (category === "SLEEP") return false;
    /* DISEASE_CARE 그룹은 없음(개인만) → step3 있음 */
    /* NO_SMOKING / NO_ALCOHOL / WATER / MEDITATION 그룹은 step3 없음 */
    return true;
  }
  return false;
}

/* ─── Step4 유효성 검사 ─── */
function isStep4Valid(form: WizardFormState): boolean {
  if (form.title.trim().length < 2) return false;
  const { category, scope, step3Mode, sub_category, goal_config } = form;

  /* WATER */
  if (category === "WATER") {
    if (!goal_config.amount?.value) return false;
    if (scope === "PERSONAL" && step3Mode === "WEEKLY_COUNT" && !goal_config.weekly_target_count) return false;
    if (scope === "GROUP" && !goal_config.group_target_count) return false;
  }
  /* SLEEP 개인 */
  if (category === "SLEEP" && scope === "PERSONAL") {
    if (step3Mode === "BED_TIME" && !goal_config.sleep_time_range) return false;
    if (step3Mode === "WAKE_TIME" && !goal_config.wake_time) return false;
  }
  /* SLEEP 그룹 */
  if (category === "SLEEP" && scope === "GROUP") {
    if (!goal_config.sleep_mode) return false;
    if (!goal_config.group_target_count) return false;
  }
  /* DIET 개인 */
  if (category === "DIET" && scope === "PERSONAL") {
    if (!goal_config.diet_targets || goal_config.diet_targets.length === 0) return false;
  }
  /* WEIGHT_MANAGEMENT */
  if (category === "WEIGHT_MANAGEMENT") {
    if (!goal_config.weight_loss_mode) return false;
    if (goal_config.weight_loss_mode === "USER_INPUT" && !goal_config.weight_loss_kg) return false;
    if (scope === "GROUP" && !goal_config.group_target_members) return false;
  }
  /* DIET 그룹 */
  if (category === "DIET" && scope === "GROUP") {
    if (!goal_config.group_target_count) return false;
  }
  /* MEDITATION */
  if (category === "MEDITATION") {
    if (!goal_config.duration_minutes) return false;
    if (scope === "PERSONAL" && step3Mode === "WEEKLY_COUNT" && !goal_config.weekly_target_count) return false;
    if (scope === "GROUP" && !goal_config.group_target_count) return false;
  }
  /* EXERCISE */
  if (category === "EXERCISE") {
    if (!sub_category) return false;
    if (scope === "GROUP") {
      if (!goal_config.group_target_count) return false;
    }
  }
  return true;
}

/* ─── Step3 유효성 검사 ─── */
function isStep3Valid(form: WizardFormState): boolean {
  const { category, scope, step3Mode, sub_category } = form;
  if (category === "EXERCISE") return !!sub_category;
  if (category === "SLEEP") return !!step3Mode;
  if (category === "DIET") return !!step3Mode;
  if (category === "DISEASE_CARE") return !!step3Mode;
  /* WATER / MEDITATION / NO_SMOKING / NO_ALCOHOL 개인 */
  if (scope === "PERSONAL") return !!step3Mode;
  return true;
}

/* ─── 기본값 ─── */
const initialForm: WizardFormState = {
  scope: "PERSONAL",
  visibility: "PUBLIC",
  category: null,
  sub_category: null,
  step3Mode: null,
  goal_type: "CHECK",
  goal_value: 1,
  duration_days: 14,
  title: "",
  max_participants: 3,
  verification_type: "CHECK",
  cadence: null,
  goal_config: {},
};

/* ─── 기본 제목 생성 ─── */
function buildDefaultTitle(form: WizardFormState): string {
  if (!form.category) return "";
  const CAT_LABELS: Record<ChallengeCategory, string> = {
    EXERCISE: "운동",
    WATER: "물 마시기",
    SLEEP: "수면",
    DIET: "식단",
    NO_SMOKING: "금연",
    NO_ALCOHOL: "금주",
    DISEASE_CARE: "질환 관리",
    MEDITATION: "명상",
    WEIGHT_MANAGEMENT: "체중 관리",
  };
  const STEP3_LABELS: Record<string, string> = {
    WALKING: "걷기", RUNNING: "러닝", STRENGTH: "근력",
    CYCLING: "자전거", SWIMMING: "수영", OTHER: "기타 운동",
    BED_TIME: "취침 시간", SLEEP_DURATION: "수면 시간", WAKE_TIME: "기상 시간",
    AVOID: "피하기", INCLUDE: "먹기", WEIGHT: "체중 관리",
    DIABETIC_FOOT_DAILY: "당뇨발 관리",
    DAILY: "", WEEKLY_COUNT: "주간",
  };
  const scopeLabel = form.scope === "GROUP" ? "그룹 " : "";
  const catLabel = CAT_LABELS[form.category] ?? form.category;
  const sub = form.sub_category ? (STEP3_LABELS[form.sub_category] ?? "") : "";
  const mode =
    !sub && form.step3Mode ? (STEP3_LABELS[form.step3Mode] ?? "") : "";
  const detail = sub || mode;
  return `${scopeLabel}${catLabel}${detail ? " · " + detail : ""} 챌린지`;
}

const STEP_LABELS = ["참여 방식", "주제", "세부 설정", "목표 설정"];

export default function NewChallengePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const createMutation = useCreateChallenge();

  const [form, setForm] = useState<WizardFormState>(initialForm);
  const [currentStep, setCurrentStep] = useState(1);

  const updateForm = useCallback((partial: Partial<WizardFormState>) => {
    setForm((prev) => ({ ...prev, ...partial }));
  }, []);

  /* ─── Step2: 카테고리 선택 핸들러 ─── */
  const handleCategoryChange = useCallback(
    (cat: ChallengeCategory) => {
      const skip = shouldSkipStep3(form.scope, cat);
      const vType = inferVerificationType(cat);
      const gType = inferGoalType(cat);
      const isGroup = form.scope === "GROUP";

      /* 그룹 카테고리별 goal_config 기본값 설정 — 버튼이 처음부터 활성화되도록 */
      let newGoalConfig: Record<string, unknown> = {};
      if (cat === "DISEASE_CARE") {
        newGoalConfig = { questionnaire_template: undefined };
      } else if (isGroup) {
        if (cat === "WATER") {
          newGoalConfig = { amount: { value: 1500, unit: "mL" }, group_target_count: 6 };
        } else if (cat === "MEDITATION") {
          newGoalConfig = { duration_minutes: 5, group_target_count: 6 };
        } else if (cat === "WEIGHT_MANAGEMENT") {
          newGoalConfig = { kind: "WEIGHT", weight_loss_mode: "MAINTAIN", group_target_members: 3 };
        } else if (cat === "NO_SMOKING" || cat === "NO_ALCOHOL") {
          /* GROUP_MEMBERS 기본값 — max_participants(3)와 동기화 */
          newGoalConfig = { group_target_members: 3 };
        } else {
          /* EXERCISE, SLEEP, DIET 그룹 — group_target_count 기본값 */
          newGoalConfig = { group_target_count: 6 };
        }
      }

      updateForm({
        category: cat,
        sub_category: null,
        step3Mode: null,
        verification_type: vType,
        goal_type: gType,
        goal_config: newGoalConfig as WizardFormState["goal_config"],
        title: "",
      });

      /* step3 건너뜀 → 바로 step4 */
      if (skip) {
        setCurrentStep(4);
      } else {
        setCurrentStep(3);
      }
    },
    [form.scope, updateForm]
  );

  /* ─── Step3: 운동 sub_category 선택 ─── */
  const handleExerciseSub = useCallback(
    (sub: ExerciseSubType) => {
      updateForm({ sub_category: sub, step3Mode: null });
    },
    [updateForm]
  );

  /* ─── Step3: step3Mode 선택 ─── */
  const handleStep3Mode = useCallback(
    (mode: string) => {
      const vType =
        form.category
          ? inferVerificationType(form.category)
          : form.verification_type;

      /* DIET step3Mode에 diet_type 저장 (그룹 식단 종류) */
      const isDietGroupType =
        form.category === "DIET" &&
        form.scope === "GROUP" &&
        ["MEDITERRANEAN", "LOW_CARB", "LOW_FAT", "LOW_SODIUM", "LOW_SUGAR"].includes(mode);

      /* DISEASE_CARE: step3Mode = questionnaire_template */
      const isDiseaseTemplate = form.category === "DISEASE_CARE";

      const newGoalConfig = isDietGroupType
        ? {
            ...form.goal_config,
            diet_type: mode as
              | "MEDITERRANEAN"
              | "LOW_CARB"
              | "LOW_FAT"
              | "LOW_SODIUM"
              | "LOW_SUGAR",
          }
        : isDiseaseTemplate
        ? { ...form.goal_config, questionnaire_template: mode }
        : form.goal_config;

      updateForm({
        step3Mode: mode,
        verification_type: vType,
        goal_config: newGoalConfig,
      });
    },
    [form, updateForm]
  );

  /* ─── 다음 버튼 ─── */
  const handleNext = useCallback(() => {
    setCurrentStep((s) => Math.min(s + 1, 4));
  }, []);

  /* ─── 이전 버튼 ─── */
  const handleBack = useCallback(() => {
    if (currentStep === 4 && form.category) {
      const skip = shouldSkipStep3(form.scope, form.category);
      setCurrentStep(skip ? 2 : 3);
      return;
    }
    setCurrentStep((s) => Math.max(s - 1, 1));
  }, [currentStep, form.category, form.scope]);

  /* ─── 제출 ─── */
  const handleSubmit = useCallback(async () => {
    if (!form.category) {
      showToast("카테고리를 선택해주세요", "error");
      return;
    }
    if (form.title.trim().length < 2) {
      showToast("챌린지 이름을 2자 이상 입력해주세요", "error");
      return;
    }

    const today = new Date();
    const resolvedCadence = inferCadence(form.scope, form.category, form.step3Mode);

    /* GROUP_SUM(물/명상/운동/식단/수면 그룹)과 WEEKLY_COUNT(개인 주간)은 7일 고정 */
    const isWeeklyFixed =
      resolvedCadence === "WEEKLY_COUNT" ||
      resolvedCadence === "GROUP_SUM";

    const durationDays = isWeeklyFixed ? 7 : form.duration_days;
    const endDate = new Date(today);
    endDate.setDate(today.getDate() + durationDays - 1);

    const startDateStr = format(today, "yyyy-MM-dd");
    const endDateStr = format(endDate, "yyyy-MM-dd");

    /* goal_config 최종 정리 */
    const finalGoalConfig = { ...form.goal_config };
    /* SLEEP_DURATION 고정값 삽입 */
    if (form.step3Mode === "SLEEP_DURATION") {
      finalGoalConfig.sleep_mode = "SLEEP_DURATION";
      finalGoalConfig.sleep_duration_hours = 7;
    }

    createMutation.mutate(
      {
        title: form.title,
        category: form.category,
        sub_category: form.sub_category ?? undefined,
        scope: form.scope,
        goal_type: form.goal_type,
        goal_value: form.goal_value || 1,
        start_date: startDateStr,
        end_date: endDateStr,
        max_participants:
          form.scope === "GROUP" ? form.max_participants : undefined,
        verification_type: form.verification_type,
        cadence: resolvedCadence,
        goal_config: Object.keys(finalGoalConfig).length > 0 ? finalGoalConfig : undefined,
        visibility: form.scope === "GROUP" ? form.visibility : undefined,
      },
      {
        onSuccess: (data) => {
          showToast("챌린지가 만들어졌어요!", "success");
          router.push(`/challenges/${data.id}`);
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  }, [form, createMutation, router, showToast]);

  /* ─── 각 스텝 제목 자동 채우기 트리거 ─── */
  const handleStep4Enter = useCallback(() => {
    if (!form.title) {
      const defaultTitle = buildDefaultTitle(form);
      if (defaultTitle) updateForm({ title: defaultTitle });
    }
  }, [form, updateForm]);

  /* ─── 스텝 전환 처리 ─── */
  const goNext = useCallback(() => {
    if (currentStep === 3) {
      /* EXERCISE: sub_category 없으면 step4 못 감 */
      if (form.category === "EXERCISE" && !form.sub_category) {
        showToast("운동 종류를 선택해주세요", "error");
        return;
      }
      handleStep4Enter();
    }
    if (currentStep === 4) {
      handleSubmit();
      return;
    }
    handleNext();
  }, [currentStep, form, handleNext, handleStep4Enter, handleSubmit, showToast]);

  /* ─── 다음 버튼 비활성화 조건 ─── */
  const nextDisabled: boolean = (() => {
    switch (currentStep) {
      case 1: return !form.scope;
      case 2: return !form.category;
      case 3: return !isStep3Valid(form);
      case 4: return !isStep4Valid(form);
      default: return false;
    }
  })();

  const isLastStep = currentStep === 4;

  return (
    <WizardShell
      currentStep={currentStep}
      totalSteps={4}
      stepLabels={STEP_LABELS}
      onBack={currentStep > 1 ? handleBack : undefined}
      onNext={goNext}
      nextLabel={isLastStep ? "챌린지 시작" : "다음"}
      nextDisabled={nextDisabled}
      nextLoading={createMutation.isPending}
    >
      {currentStep === 1 && (
        <WizardStep1
          value={form.scope}
          onChange={(scope: ChallengeScope) => {
            updateForm({ scope, step3Mode: null, goal_config: {} });
          }}
          visibility={form.visibility}
          onVisibilityChange={(v: ChallengeVisibility) => updateForm({ visibility: v })}
        />
      )}

      {currentStep === 2 && (
        <WizardStep2
          value={form.category}
          onChange={handleCategoryChange}
        />
      )}

      {currentStep === 3 && (
        <WizardStep3
          form={form}
          onExerciseSub={handleExerciseSub}
          onStep3Mode={handleStep3Mode}
        />
      )}

      {currentStep === 4 && (
        <WizardStep4 form={form} onChange={updateForm} />
      )}
    </WizardShell>
  );
}
