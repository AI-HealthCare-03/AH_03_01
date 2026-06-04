"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import WizardShell from "@/components/health/new/WizardShell";
import StepBasic from "@/components/health/new/StepBasic";
import StepBP from "@/components/health/new/StepBP";
import StepGlucose from "@/components/health/new/StepGlucose";
import { useCreateProfile } from "@/hooks/queries/useCreateProfile";
import { useCreateHealthRecord } from "@/hooks/queries/useCreateHealthRecord";
import { useCreatePrediction } from "@/hooks/queries/useCreatePrediction";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { pushNotification } from "@/components/layout/NotificationDropdown";
import type {
  WizardFormStep1,
  WizardFormStep2,
  WizardFormStep3,
} from "@/types/health";

/* 프론트 enum → 백엔드 enum/bool 변환 매핑.
   백엔드 HealthProfileUpsertRequest 는 is_smoker(bool), alcohol_intake(NONE|LIGHT|MODERATE|HEAVY),
   has_diabetes_family_history(bool), has_hypertension_family_history(bool), is_chronic_patient(bool),
   pregnancy_history(NONE|PREGNANT|POSTPARTUM|NOT_APPLICABLE), diseases(string[]) 를 받는다. */
const ALCOHOL_MAP: Record<string, "NONE" | "LIGHT" | "MODERATE" | "HEAVY"> = {
  NONE: "NONE",
  WEEKLY_1_2: "LIGHT",
  WEEKLY_3_4: "MODERATE",
  DAILY: "HEAVY",
};
const PREGNANCY_MAP: Record<string, "NONE" | "PREGNANT" | "POSTPARTUM" | "NOT_APPLICABLE"> = {
  NONE: "NOT_APPLICABLE",
  PREGNANT: "PREGNANT",
  POSTPARTUM: "POSTPARTUM",
};

/* 백엔드 호환 페이로드 타입 */
interface BackendProfilePayload {
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  is_smoker?: boolean;
  alcohol_intake?: "NONE" | "LIGHT" | "MODERATE" | "HEAVY";
  has_diabetes_family_history?: boolean;
  has_hypertension_family_history?: boolean;
  is_chronic_patient?: boolean;
  diseases?: string[];
  pregnancy_history?: "NONE" | "PREGNANT" | "POSTPARTUM" | "NOT_APPLICABLE";
}

type Step = 1 | 2 | 3;

export default function HealthRecordsNewPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [step, setStep] = useState<Step>(1);

  const createProfile = useCreateProfile();
  const createRecord = useCreateHealthRecord();
  const createPrediction = useCreatePrediction();

  const isLoading =
    createProfile.isPending || createRecord.isPending || createPrediction.isPending;

  /* ── Step 1: 기본 정보 저장 ──────── */

  const handleStep1 = async (data: WizardFormStep1) => {
    /* 백엔드 실제 DTO 키로 변환해서 보낸다. */
    const diseases = data.chronic_diseases.filter((d) => d !== "NONE");
    const body: BackendProfilePayload = {
      height_cm: data.height_cm ? parseFloat(data.height_cm) : undefined,
      weight_kg: data.weight_kg ? parseFloat(data.weight_kg) : undefined,
      waist_cm: data.waist_cm ? parseFloat(data.waist_cm) : undefined,
      is_smoker: data.smoking_status === "CURRENT",
      alcohol_intake: ALCOHOL_MAP[data.alcohol_frequency] ?? "NONE",
      has_diabetes_family_history: !!data.family_history_diabetes,
      has_hypertension_family_history: !!data.family_history_hypertension,
      is_chronic_patient: diseases.length > 0,
      diseases,

      pregnancy_history: PREGNANCY_MAP[data.pregnancy_status] ?? "NOT_APPLICABLE",
    };

    try {
      /* createProfile 의 타입이 프론트 키를 받지만 실제 호출은 객체 그대로 전달 */
      await createProfile.mutateAsync(body as unknown as Parameters<typeof createProfile.mutateAsync>[0]);
      setStep(2);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 2: 혈압 저장 ─────────── */

  const handleStep2 = async (data: WizardFormStep2) => {
    try {
      await createRecord.mutateAsync({
        record_type: "BLOOD_PRESSURE",
        sub_type: data.measurement_env,
        primary_value: parseFloat(data.systolic),
        secondary_value: parseFloat(data.diastolic),
        unit: "mmHg",
        measured_at: format(new Date(), "yyyy-MM-dd'T'HH:mm:ssxxx"),
      });
      setStep(3);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 2 건너뛰기 ─────────────── */

  const handleSkipBP = () => setStep(3);

  /* ── Step 3: 혈당/HbA1c 저장 + 예측 ── */

  const handleStep3 = async (data: WizardFormStep3, skip = false) => {
    if (!skip) {
      const now = format(new Date(), "yyyy-MM-dd'T'HH:mm:ssxxx");
      const requests: Promise<unknown>[] = [];

      if (data.fasting_glucose) {
        requests.push(
          createRecord.mutateAsync({
            record_type: "BLOOD_GLUCOSE",
            sub_type: "FASTING",
            primary_value: parseFloat(data.fasting_glucose),
            unit: "mg/dL",
            measured_at: now,
          })
        );
      }
      if (data.postmeal_glucose) {
        requests.push(
          createRecord.mutateAsync({
            record_type: "BLOOD_GLUCOSE",
            sub_type: "POSTMEAL",
            primary_value: parseFloat(data.postmeal_glucose),
            unit: "mg/dL",
            measured_at: now,
          })
        );
      }
      if (data.hba1c) {
        requests.push(
          createRecord.mutateAsync({
            record_type: "HBA1C",
            primary_value: parseFloat(data.hba1c),
            unit: "%",
            measured_at: now,
          })
        );
      }

      try {
        await Promise.allSettled(requests);
      } catch {
        /* 개별 실패는 allSettled가 처리 — 예측은 계속 시도 */
      }
    }

    /* 예측 생성 — 같은 입력으로 3개 질병 모두 호출.
       하나라도 성공하면 risk 탭에서 결과 표시 가능. 모두 실패해도 이동은 진행. */
    // 이전 위험도 저장값 읽기 (변화 감지용)
    const PREV_RISK_KEY = "prev-risk-levels";
    let prevRisk: Record<string, string> = {};
    try {
      const raw = localStorage.getItem(PREV_RISK_KEY);
      if (raw) prevRisk = JSON.parse(raw);
    } catch { /* 무시 */ }

    const DISEASE_LABEL: Record<string, string> = {
      HYPERTENSION: "고혈압",
      DIABETES: "당뇨",
      CARDIOVASCULAR: "심혈관",
    };
    const RISK_LABEL: Record<string, string> = {
      NORMAL: "정상",
      CAUTION: "주의",
      RISK: "위험",
      HIGH_RISK: "고위험",
    };

    const predictionResults = await Promise.allSettled([
      createPrediction.mutateAsync("HYPERTENSION"),
      createPrediction.mutateAsync("DIABETES"),
      createPrediction.mutateAsync("CARDIOVASCULAR"),
    ]);

    // 위험도 변화 감지 → 알림
    const nextRisk: Record<string, string> = { ...prevRisk };
    predictionResults.forEach((result) => {
      if (result.status !== "fulfilled") return;
      const pred = result.value;
      const diseaseType: string = pred.disease_type ?? "";
      const newLevel: string = pred.risk_level ?? "";
      const oldLevel: string = prevRisk[diseaseType] ?? "";

      nextRisk[diseaseType] = newLevel;

      if (newLevel && oldLevel && oldLevel !== newLevel) {
        const dLabel = DISEASE_LABEL[diseaseType] ?? diseaseType;
        const from = RISK_LABEL[oldLevel] ?? oldLevel;
        const to = RISK_LABEL[newLevel] ?? newLevel;
        pushNotification({
          category: "위험도",
          title: `⚠️ ${dLabel} 위험도 변화`,
          body: `${dLabel} 위험도가 ${from}에서 ${to}로 변경되었어요.`,
        });
      }
    });

    // 새 위험도 저장
    try { localStorage.setItem(PREV_RISK_KEY, JSON.stringify(nextRisk)); } catch { /* 무시 */ }

    const succeeded = predictionResults.filter((r) => r.status === "fulfilled").length;
    if (succeeded === 3) {
      showToast("위험도 분석이 완료되었습니다.", "success");
    } else if (succeeded > 0) {
      showToast(`위험도 분석 일부 완료 (${succeeded}/3)`, "warning");
    } else {
      showToast("위험도 계산에 실패했습니다. 나중에 다시 시도해 주세요.", "warning");
    }

    router.push("/health-records?tab=risk");
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm text-text-secondary hover:text-text-primary flex items-center gap-1 mb-3"
        >
          ← 뒤로
        </button>
        <h1 className="text-xl font-black text-text-primary">건강 기록 입력</h1>
        <p className="text-sm text-text-secondary mt-1">
          Step 1은 필수, 2·3단계는 건너뛸 수 있습니다.
        </p>
      </div>

      <WizardShell currentStep={step}>
        {step === 1 && (
          <StepBasic onSubmit={handleStep1} isLoading={createProfile.isPending} />
        )}
        {step === 2 && (
          <StepBP
            onSubmit={handleStep2}
            onSkip={handleSkipBP}
            isLoading={createRecord.isPending}
          />
        )}
        {step === 3 && (
          <StepGlucose
            onSubmit={handleStep3}
            onSkip={() => handleStep3({ fasting_glucose: "", postmeal_glucose: "", hba1c: "" }, true)}
            isLoading={isLoading}
          />
        )}
      </WizardShell>
    </div>
  );
}
