"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import WizardShell from "@/components/health/new/WizardShell";
import StepMeasure from "@/components/health/new/StepMeasure";
import StepVitals from "@/components/health/new/StepVitals";
import StepFamily from "@/components/health/new/StepFamily";
import StepSmokingDrinking from "@/components/health/new/StepSmokingDrinking";
import StepActivity from "@/components/health/new/StepActivity";
import StepDiet from "@/components/health/new/StepDiet";
import StepExtras from "@/components/health/new/StepExtras";
import { useCreateProfile } from "@/hooks/queries/useCreateProfile";
import { useCreateHealthRecord } from "@/hooks/queries/useCreateHealthRecord";
import { useCreatePrediction } from "@/hooks/queries/useCreatePrediction";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { pushNotification } from "@/components/layout/NotificationDropdown";
import type {
  WizardFormStep1,
  WizardFormStep2,
  WizardFormStep3,
  WizardFormStep4,
  WizardFormStep5,
  WizardFormStep6,
  WizardFormStep7,
  HealthProfileUpsertRequest,
} from "@/types/health";

type Step = 1 | 2 | 3 | 4 | 5 | 6 | 7;

/* 흡연 UI 선택 → current_smoker / smoking_risk 변환 */
function smokingToFields(choice: WizardFormStep4["smoking_choice"]): {
  current_smoker: number;
  smoking_risk: number;
} {
  if (choice === "CURRENT") return { current_smoker: 1, smoking_risk: 1.0 };
  if (choice === "QUIT") return { current_smoker: 0, smoking_risk: 0.5 };
  return { current_smoker: 0, smoking_risk: 0.0 };
}

/* 문자열 입력 → 숫자. 빈값/비정상(NaN·Infinity)은 undefined(미전송). */
function toNum(s: string): number | undefined {
  if (s.trim() === "") return undefined;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : undefined;
}
/* 정수 백엔드 필드(mid_act_day/walk_day/water_count)용 — 소수 입력 방지. */
function toInt(s: string): number | undefined {
  if (s.trim() === "") return undefined;
  const n = parseInt(s, 10);
  return Number.isFinite(n) ? n : undefined;
}

export default function HealthRecordsNewPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [step, setStep] = useState<Step>(1);

  const { data: me } = useMe();
  const gender = me?.gender;

  const createProfile = useCreateProfile();
  const createRecord = useCreateHealthRecord();
  const createPrediction = useCreatePrediction();

  const isLoading =
    createProfile.isPending || createRecord.isPending || createPrediction.isPending;

  /* 스텝 간 누적 페이로드 — 각 스텝이 완료될 때마다 병합 */
  const [accumulated, setAccumulated] = useState<HealthProfileUpsertRequest>({});

  /* 프로필 upsert helper */
  const upsert = async (patch: HealthProfileUpsertRequest) => {
    const merged = { ...accumulated, ...patch };
    setAccumulated(merged);
    await createProfile.mutateAsync(merged);
  };

  /* ── Step 1: 신체계측 ──────────────────── */
  const handleStep1 = async (data: WizardFormStep1) => {
    const patch: HealthProfileUpsertRequest = {};
    const height = toNum(data.height_cm);
    const weight = toNum(data.weight_kg);
    const waist = toNum(data.waist_cm);
    if (height !== undefined) patch.height_cm = height;
    if (weight !== undefined) patch.weight_kg = weight;
    if (waist !== undefined) patch.waist_cm = waist;

    try {
      await upsert(patch);

      /* 시계열: 체중, 허리둘레 */
      const now = format(new Date(), "yyyy-MM-dd'T'HH:mm:ssxxx");
      const timeRecords: Promise<unknown>[] = [];
      if (weight !== undefined) {
        timeRecords.push(
          createRecord.mutateAsync({
            record_type: "WEIGHT",
            primary_value: weight,
            unit: "kg",
            measured_at: now,
          })
        );
      }
      if (waist !== undefined) {
        timeRecords.push(
          createRecord.mutateAsync({
            record_type: "WAIST",
            primary_value: waist,
            unit: "cm",
            measured_at: now,
          })
        );
      }
      await Promise.allSettled(timeRecords);
      setStep(2);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 2: 혈압·혈당 ─────────────────── */
  const handleStep2 = async (data: WizardFormStep2) => {
    const patch: HealthProfileUpsertRequest = {
      bp_measure_env: data.measurement_env,
    };
    const systolic = toNum(data.systolic);
    const diastolic = toNum(data.diastolic);
    const fasting = toNum(data.fasting_glucose);
    if (systolic !== undefined) patch.systolic_bp = systolic;
    if (diastolic !== undefined) patch.diastolic_bp = diastolic;
    if (fasting !== undefined) patch.fasting_blood_sugar = fasting;

    try {
      await upsert(patch);

      /* 시계열 */
      const now = format(new Date(), "yyyy-MM-dd'T'HH:mm:ssxxx");
      const timeRecords: Promise<unknown>[] = [];
      if (systolic !== undefined && diastolic !== undefined) {
        timeRecords.push(
          createRecord.mutateAsync({
            record_type: "BLOOD_PRESSURE",
            sub_type: data.measurement_env,
            primary_value: systolic,
            secondary_value: diastolic,
            unit: "mmHg",
            measured_at: now,
          })
        );
      }
      if (fasting !== undefined) {
        timeRecords.push(
          createRecord.mutateAsync({
            record_type: "BLOOD_GLUCOSE",
            sub_type: "FASTING",
            primary_value: fasting,
            unit: "mg/dL",
            measured_at: now,
          })
        );
      }
      await Promise.allSettled(timeRecords);
      setStep(3);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 3: 가족력 ────────────────────── */
  const handleStep3 = async (data: WizardFormStep3) => {
    const patch: HealthProfileUpsertRequest = {
      family_dm: data.family_dm,
      family_hp: data.family_hp,
      family_hl: data.family_hl,
    };
    try {
      await upsert(patch);
      setStep(4);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 4: 흡연·음주 ─────────────────── */
  const handleStep4 = async (data: WizardFormStep4) => {
    const { current_smoker, smoking_risk } = smokingToFields(data.smoking_choice);
    const patch: HealthProfileUpsertRequest = { current_smoker, smoking_risk };

    if (data.alcohol_freq_y !== null) {
      patch.alcohol_freq_y = data.alcohol_freq_y;
      /* alcohol_freq_y=1(전혀 안 마심) 이 아닐 때만 음주량 전송 */
      if (data.alcohol_freq_y !== 1 && data.alcohol_cup !== null) {
        patch.alcohol_cup = data.alcohol_cup;
      }
    }

    try {
      await upsert(patch);
      setStep(5);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 5: 수면·운동·수분 ─────────────── */
  const handleStep5 = async (data: WizardFormStep5) => {
    const patch: HealthProfileUpsertRequest = {};
    const sleepWd = toNum(data.sleep_weekday);
    const sleepWe = toNum(data.sleep_weekend);
    const modHour = toNum(data.moderate_exercise_hour);
    const midActDay = toInt(data.mid_act_day);
    const walkDay = toInt(data.walk_day);
    const waterCount = toInt(data.water_count);
    if (sleepWd !== undefined) patch.sleep_weekday = sleepWd;
    if (sleepWe !== undefined) patch.sleep_weekend = sleepWe;
    if (modHour !== undefined) patch.moderate_exercise_hour = modHour;
    if (midActDay !== undefined) patch.mid_act_day = midActDay;
    if (walkDay !== undefined) patch.walk_day = walkDay;
    if (waterCount !== undefined) patch.water_count = waterCount;

    try {
      await upsert(patch);
      setStep(6);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 6: 식습관 ────────────────────── */
  const handleStep6 = async (data: WizardFormStep6) => {
    const patch: HealthProfileUpsertRequest = {};
    if (data.veg_freq_1 !== null) patch.veg_freq_1 = data.veg_freq_1;
    if (data.fruit_freq !== null) patch.fruit_freq = data.fruit_freq;
    if (data.out_meal_freq !== null) patch.out_meal_freq = data.out_meal_freq;
    if (data.breakfast_freq !== null) patch.breakfast_freq = data.breakfast_freq;

    try {
      await upsert(patch);
      setStep(7);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  /* ── Step 7: 추가 정보 + 예측 트리거 ─────── */
  const handleStep7 = async (data: WizardFormStep7) => {
    const patch: HealthProfileUpsertRequest = {
      chronic_diseases: data.chronic_diseases,
      pregnancy_status: data.pregnancy_status,
    };

    /* is_menopause: StepExtras 가 결정 (여성=선택값|null, 남성=-1, 성별 미상=null). null이면 미전송. */
    if (data.is_menopause !== null) {
      patch.is_menopause = data.is_menopause;
    }

    /* ocp_total_months: 복용 중이면 개월수, 아니면 0 */
    if (gender === "FEMALE") {
      if (data.ocp_taking === true) {
        patch.ocp_total_months = toInt(data.ocp_total_months) ?? 0;
      } else if (data.ocp_taking === false) {
        patch.ocp_total_months = 0;
      }
    }

    /* anemia: 모름=null → 키 자체 미포함(undefined) */
    if (data.anemia !== null && data.anemia !== undefined) {
      patch.anemia = data.anemia;
    }

    try {
      await upsert(patch);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
      /* 프로필 저장 실패해도 예측은 시도 */
    }

    /* 예측 생성 — 같은 입력으로 3개 질병 모두 호출.
       하나라도 성공하면 risk 탭에서 결과 표시 가능. 모두 실패해도 이동은 진행. */
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
          title: `${dLabel} 위험도 변화`,
          body: `${dLabel} 위험도가 ${from}에서 ${to}로 변경되었어요.`,
        });
      }
    });

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
          1단계는 필수, 나머지는 건너뛸 수 있습니다.
        </p>
      </div>

      <WizardShell currentStep={step}>
        {step === 1 && (
          <StepMeasure
            onSubmit={handleStep1}
            isLoading={createProfile.isPending || createRecord.isPending}
          />
        )}
        {step === 2 && (
          <StepVitals
            onSubmit={handleStep2}
            onSkip={() => setStep(3)}
            isLoading={createProfile.isPending || createRecord.isPending}
          />
        )}
        {step === 3 && (
          <StepFamily
            onSubmit={handleStep3}
            onSkip={() => setStep(4)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 4 && (
          <StepSmokingDrinking
            onSubmit={handleStep4}
            onSkip={() => setStep(5)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 5 && (
          <StepActivity
            onSubmit={handleStep5}
            onSkip={() => setStep(6)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 6 && (
          <StepDiet
            onSubmit={handleStep6}
            onSkip={() => setStep(7)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 7 && (
          <StepExtras
            gender={gender}
            onSubmit={handleStep7}
            isLoading={isLoading}
          />
        )}
      </WizardShell>
    </div>
  );
}
