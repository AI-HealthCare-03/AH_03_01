"use client";

import { useState, useEffect } from "react";
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
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { fetchHealthProfileDetail, fetchHealthRecordList } from "@/lib/api/health";
import type {
  WizardFormStep1,
  WizardFormStep2,
  WizardFormStep3,
  WizardFormStep4,
  WizardFormStep5,
  WizardFormStep6,
  WizardFormStep7,
  HealthProfileUpsertRequest,
  HealthProfileDetail,
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

/* 기존 프로필 → 흡연 UI 선택값으로 역변환 */
function smokingChoiceFromProfile(
  p: HealthProfileDetail
): WizardFormStep4["smoking_choice"] | undefined {
  if (p.current_smoker === undefined) return undefined;
  if (p.current_smoker === 1) return "CURRENT";
  if (p.smoking_risk !== undefined && p.smoking_risk !== null && p.smoking_risk > 0) return "QUIT";
  return "NEVER";
}

export default function HealthRecordsNewPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [step, setStep] = useState<Step>(1);

  const { data: me } = useMe();
  const gender = me?.gender;

  const createProfile = useCreateProfile();
  const createRecord = useCreateHealthRecord();

  const isLoading =
    createProfile.isPending || createRecord.isPending;

  /* 스텝 간 누적 페이로드 — 각 스텝이 완료될 때마다 병합 */
  const [accumulated, setAccumulated] = useState<HealthProfileUpsertRequest>({});

  /* 기존 프로필 로드 — 수정 모드 판별 */
  const [existingProfile, setExistingProfile] = useState<HealthProfileDetail | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);
  /* 몸무게·허리둘레는 프로필보다 갱신이 잦은 일별 기록의 최신값을 우선 prefill 한다
     (프로필은 갱신이 드물어 옛 값이 채워지던 문제). 키는 일별 기록이 없어 프로필 사용. */
  const [latestWeightKg, setLatestWeightKg] = useState<number | undefined>(undefined);
  const [latestWaistCm, setLatestWaistCm] = useState<number | undefined>(undefined);
  /* 이미 방문한(또는 prefill된) 단계 번호 집합 — 수정 모드에서만 클릭 이동 허용 */
  const [visitedSteps, setVisitedSteps] = useState<Set<number>>(new Set([1]));
  /* 수정 모드 = 기존 프로필 존재 */
  const isEditMode = profileLoaded && existingProfile !== null;

  useEffect(() => {
    Promise.all([
      fetchHealthProfileDetail(),
      fetchHealthRecordList({ recordType: "WEIGHT", size: 1 }),
      fetchHealthRecordList({ recordType: "WAIST", size: 1 }),
    ]).then(([profile, weightList, waistList]) => {
      if (profile) {
        setExistingProfile(profile);
        /* 수정 모드: 모든 단계를 방문 가능으로 표시 */
        setVisitedSteps(new Set([1, 2, 3, 4, 5, 6, 7]));
      }
      if (weightList?.[0]?.primary_value) setLatestWeightKg(parseFloat(weightList[0].primary_value));
      if (waistList?.[0]?.primary_value) setLatestWaistCm(parseFloat(waistList[0].primary_value));
      setProfileLoaded(true);
    });
  }, []);

  /* prefill 헬퍼 — 기존 프로필/최신 기록에서 각 스텝 defaultValues 생성 */
  const prefillStep1 = (): Partial<WizardFormStep1> | undefined => {
    const p = existingProfile;
    /* 몸무게·허리둘레: 최신 기록 우선 → 프로필 폴백. 키: 프로필. */
    const weight = latestWeightKg ?? (p?.weight_kg != null ? Number(p.weight_kg) : undefined);
    const waist = latestWaistCm ?? (p?.waist_cm != null ? Number(p.waist_cm) : undefined);
    if (!p && weight === undefined && waist === undefined) return undefined;
    return {
      height_cm: p?.height_cm != null ? String(p.height_cm) : "",
      weight_kg: weight !== undefined ? String(weight) : "",
      waist_cm: waist !== undefined ? String(waist) : "",
    };
  };

  const prefillStep2 = (): Partial<WizardFormStep2> | undefined => {
    if (!existingProfile) return undefined;
    const p = existingProfile;
    return {
      systolic: p.systolic_bp !== undefined ? String(p.systolic_bp) : "",
      diastolic: p.diastolic_bp !== undefined ? String(p.diastolic_bp) : "",
      fasting_glucose: p.fasting_blood_sugar !== undefined ? String(p.fasting_blood_sugar) : "",
      measurement_env: p.bp_measure_env ?? "HOME",
    };
  };

  const prefillStep3 = (): Partial<WizardFormStep3> | undefined => {
    if (!existingProfile) return undefined;
    const p = existingProfile;
    return {
      family_dm: p.family_dm ?? -1,
      family_hp: p.family_hp ?? -1,
      family_hl: p.family_hl ?? -1,
    };
  };

  const prefillStep4 = (): Partial<WizardFormStep4> | undefined => {
    if (!existingProfile) return undefined;
    const p = existingProfile;
    return {
      smoking_choice: smokingChoiceFromProfile(p),
      alcohol_freq_y: p.alcohol_freq_y ?? null,
      alcohol_cup: p.alcohol_cup ?? null,
    };
  };

  const prefillStep5 = (): Partial<WizardFormStep5> | undefined => {
    if (!existingProfile) return undefined;
    const p = existingProfile;
    return {
      sleep_weekday: p.sleep_weekday !== undefined ? String(p.sleep_weekday) : "",
      sleep_weekend: p.sleep_weekend !== undefined ? String(p.sleep_weekend) : "",
      moderate_exercise_hour: p.moderate_exercise_hour !== undefined ? String(p.moderate_exercise_hour) : "",
      mid_act_day: p.mid_act_day !== undefined ? String(p.mid_act_day) : "",
      walk_day: p.walk_day !== undefined ? String(p.walk_day) : "",
      water_count: p.water_count !== undefined ? String(p.water_count) : "",
    };
  };

  const prefillStep6 = (): Partial<WizardFormStep6> | undefined => {
    if (!existingProfile) return undefined;
    const p = existingProfile;
    return {
      veg_freq_1: p.veg_freq_1 ?? null,
      fruit_freq: p.fruit_freq ?? null,
      out_meal_freq: p.out_meal_freq ?? null,
      breakfast_freq: p.breakfast_freq ?? null,
    };
  };

  const prefillStep7 = (): Partial<WizardFormStep7> | undefined => {
    if (!existingProfile) return undefined;
    const p = existingProfile;
    return {
      is_menopause: p.is_menopause ?? null,
      ocp_taking: p.ocp_total_months !== undefined && p.ocp_total_months > 0 ? true : null,
      ocp_total_months: p.ocp_total_months !== undefined ? String(p.ocp_total_months) : "",
      anemia: p.anemia ?? null,
      chronic_diseases: p.chronic_diseases ?? ["NONE"],
      pregnancy_status: (p.pregnancy_status as WizardFormStep7["pregnancy_status"]) ?? "NOT_APPLICABLE",
    };
  };

  /* 단계 이동 + visitedSteps 기록 */
  const goToStep = (s: Step) => {
    setStep(s);
    setVisitedSteps((prev) => new Set([...prev, s]));
  };

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
      goToStep(2);
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
      goToStep(3);
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
      goToStep(4);
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
      goToStep(5);
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
      goToStep(6);
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
      goToStep(7);
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

    /* anemia: 1=예 / 0=아니오 / -1=모름. null=미선택(미전송) */
    if (data.anemia !== null && data.anemia !== undefined) {
      patch.anemia = data.anemia;
    }

    try {
      await upsert(patch);
      showToast("건강 정보가 저장되었습니다.", "success");
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
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

      <WizardShell
        currentStep={step}
        clickableSteps={isEditMode ? visitedSteps : undefined}
        onStepClick={isEditMode ? (s) => setStep(s as Step) : undefined}
      >
        {step === 1 && (
          /* key: 프로필 로드는 비동기라 Step1(첫 화면)이 로드 전 마운트되면 prefill 이 비어
             react-hook-form 이 이후 defaultValues 변경을 무시한다. 로드 완료 시 remount 해
             최신 저장값(키·몸무게·허리둘레)으로 채운다. */
          <StepMeasure
            key={profileLoaded ? "profile-loaded" : "profile-loading"}
            defaultValues={prefillStep1()}
            onSubmit={handleStep1}
            isLoading={createProfile.isPending || createRecord.isPending}
          />
        )}
        {step === 2 && (
          <StepVitals
            defaultValues={prefillStep2()}
            onSubmit={handleStep2}
            onSkip={() => goToStep(3)}
            isLoading={createProfile.isPending || createRecord.isPending}
          />
        )}
        {step === 3 && (
          <StepFamily
            defaultValues={prefillStep3()}
            onSubmit={handleStep3}
            onSkip={() => goToStep(4)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 4 && (
          <StepSmokingDrinking
            defaultValues={prefillStep4()}
            onSubmit={handleStep4}
            onSkip={() => goToStep(5)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 5 && (
          <StepActivity
            defaultValues={prefillStep5()}
            onSubmit={handleStep5}
            onSkip={() => goToStep(6)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 6 && (
          <StepDiet
            defaultValues={prefillStep6()}
            onSubmit={handleStep6}
            onSkip={() => goToStep(7)}
            isLoading={createProfile.isPending}
          />
        )}
        {step === 7 && (
          <StepExtras
            gender={gender}
            defaultValues={prefillStep7()}
            onSubmit={handleStep7}
            isLoading={isLoading}
          />
        )}
      </WizardShell>
    </div>
  );
}
