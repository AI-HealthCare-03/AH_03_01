"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import WizardShell from "@/components/challenges/new/WizardShell";
import WizardStep1 from "@/components/challenges/new/WizardStep1";
import WizardStep2 from "@/components/challenges/new/WizardStep2";
import WizardStep3 from "@/components/challenges/new/WizardStep3";
import WizardStep4 from "@/components/challenges/new/WizardStep4";
import { useCreateChallenge } from "@/hooks/queries/useCreateChallenge";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type {
  WizardFormState,
  ChallengeScope,
  ChallengeCategory,
  ExerciseSubType,
} from "@/types/challenge";
import { format } from "@/lib/dateUtils";

/* =========================================
   챌린지 생성 4-Step 위저드 (10-C03~C07 / 15-C02)
   ========================================= */

/* verification_type 자동 추론 */
function inferVerificationType(
  category: ChallengeCategory
): "CHECK" | "PHOTO" {
  const checkCategories: ChallengeCategory[] = [
    "NO_ALCOHOL",
    "SLEEP",
    "MEDITATION",
  ];
  return checkCategories.includes(category) ? "CHECK" : "PHOTO";
}

const STEP_LABELS_FULL = ["참여 방식", "주제", "운동 종류", "목표"];
const STEP_LABELS_SHORT = ["참여 방식", "주제", "목표"];

const initialForm: WizardFormState = {
  scope: "PERSONAL",
  category: null,
  sub_category: null,
  goal_type: "CHECK",
  goal_value: 0,
  duration_days: 14,
  title: "",
  max_participants: 3,
  verification_type: "CHECK",
};

export default function NewChallengePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const createMutation = useCreateChallenge();

  const [form, setForm] = useState<WizardFormState>(initialForm);
  const [currentStep, setCurrentStep] = useState(1);

  const isExercise = form.category === "EXERCISE";
  const stepLabels = isExercise ? STEP_LABELS_FULL : STEP_LABELS_SHORT;
  const totalSteps = stepLabels.length;

  /* Step에서 표시할 실제 UI 스텝 번호 계산
   * Exercise: 1(범위) 2(카테고리) 3(운동종류) 4(목표)
   * 기타:     1(범위) 2(카테고리) [skip] 3(목표)
   */

  const updateForm = (partial: Partial<WizardFormState>) => {
    setForm((prev) => ({ ...prev, ...partial }));
  };

  /* 범주 선택 시 verification_type 자동 갱신 */
  const handleCategoryChange = (cat: ChallengeCategory) => {
    updateForm({
      category: cat,
      sub_category: null,
      verification_type: inferVerificationType(cat),
      title: "",
    });
    // exercise가 아니면 step3 건너뜀
    if (cat !== "EXERCISE") {
      setCurrentStep(isExercise ? 4 : 3);
    } else {
      setCurrentStep(3);
    }
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      /* 비운동 카테고리에서 step3 건너뜀 처리: step3 → step2 */
      setCurrentStep((s) => s - 1);
    }
  };

  const handleSubmit = async () => {
    if (!form.category) {
      showToast("카테고리를 선택해주세요", "error");
      return;
    }
    if (!form.title.trim()) {
      showToast("챌린지 이름을 입력해주세요", "error");
      return;
    }

    const today = new Date();
    const endDate = new Date(today);
    endDate.setDate(today.getDate() + form.duration_days - 1);

    const startDateStr = format(today, "yyyy-MM-dd");
    const endDateStr = format(endDate, "yyyy-MM-dd");

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
  };

  /* 각 스텝별 다음 버튼 활성화 조건 */
  const nextDisabledMap: Record<number, boolean> = {
    1: !form.scope,
    2: !form.category,
    3: isExercise ? !form.sub_category : !form.title.trim(),
    4: !form.title.trim(),
  };

  const isLastStep = currentStep === totalSteps;
  const nextDisabled = nextDisabledMap[currentStep] ?? false;

  return (
    <WizardShell
      currentStep={currentStep}
      totalSteps={totalSteps}
      stepLabels={stepLabels}
      onBack={currentStep > 1 ? handleBack : undefined}
      onNext={isLastStep ? handleSubmit : handleNext}
      nextLabel={isLastStep ? "챌린지 시작" : "다음"}
      nextDisabled={nextDisabled}
      nextLoading={createMutation.isPending}
    >
      {currentStep === 1 && (
        <WizardStep1
          value={form.scope}
          onChange={(scope: ChallengeScope) => updateForm({ scope })}
        />
      )}
      {currentStep === 2 && (
        <WizardStep2
          value={form.category}
          onChange={handleCategoryChange}
        />
      )}
      {currentStep === 3 && isExercise && (
        <WizardStep3
          value={form.sub_category}
          onChange={(sub: ExerciseSubType) =>
            updateForm({ sub_category: sub })
          }
        />
      )}
      {((currentStep === 3 && !isExercise) ||
        (currentStep === 4 && isExercise)) && (
        <WizardStep4 form={form} onChange={updateForm} />
      )}
    </WizardShell>
  );
}
