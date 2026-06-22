"use client";

/**
 * /health-records/complete
 * 위험도 예측에 필요한 누락 필드만 채우는 단계별 입력 화면.
 * - ProfileCompleteness.missing_fields 를 읽어 해당 필드만 표시
 * - 기존 값은 prefill (useHealthProfile + GET profile 응답)
 * - 부분 저장 후 completeness 재조회 → 충족 시 /health-records?tab=risk 이동
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { useQueryClient } from "@tanstack/react-query";
import { useProfileCompleteness, PROFILE_COMPLETENESS_KEY } from "@/hooks/queries/useProfileCompleteness";
import { useCreateProfile } from "@/hooks/queries/useCreateProfile";
import { useCreateHealthRecord } from "@/hooks/queries/useCreateHealthRecord";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { fetchHealthProfileDetail } from "@/lib/api/health";
import Button from "@/components/ui/Button";
import type { HealthProfileUpsertRequest, HealthProfileDetail } from "@/types/health";

/* ── 필드 그룹 정의 ─────────────────────── */

type FieldGroup = "measure" | "vitals" | "family" | "smoking" | "activity" | "diet" | "extras";

const FIELD_TO_GROUP: Record<string, FieldGroup> = {
  height_cm: "measure",
  weight_kg: "measure",
  waist_cm: "measure",
  systolic_bp: "vitals",
  diastolic_bp: "vitals",
  fasting_blood_sugar: "vitals",
  sleep_weekday: "activity",
  sleep_weekend: "activity",
  moderate_exercise_hour: "activity",
  mid_act_day: "activity",
  walk_day: "activity",
  water_count: "activity",
  family_dm: "family",
  family_hp: "family",
  family_hl: "family",
  alcohol_freq_y: "smoking",
  alcohol_cup: "smoking",
  current_smoker: "smoking",
  smoking_risk: "smoking",
  fruit_freq: "diet",
  veg_freq_1: "diet",
  out_meal_freq: "diet",
  breakfast_freq: "diet",
  anemia: "extras",
  is_menopause: "extras",
  ocp_total_months: "extras",
};

const GROUP_LABEL: Record<FieldGroup, string> = {
  measure: "신체 계측",
  vitals: "혈압 / 공복혈당",
  family: "가족력",
  smoking: "흡연 / 음주",
  activity: "수면 / 운동 / 수분",
  diet: "식습관",
  extras: "추가 정보",
};

/* ── 공통 NumberInput ────────────────────── */

function NumberInput({
  label,
  id,
  unit,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  id: string;
  unit: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium text-text-primary mb-1 block">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-12 px-4 pr-14 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
        />
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary">
          {unit}
        </span>
      </div>
    </div>
  );
}

/* ── 3선택 칩 ─────────────────────────────── */

function TriChip({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: number; label: string }[];
  value: number | null;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">{label}</p>
      <div className="flex gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
              value === opt.value
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── SelectChip (주파수/선택지) ────────────── */

function SelectChip({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: number; label: string }[];
  value: number | null;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "px-3 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
              value === opt.value
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* 음주 빈도 옵션 */
const ALCOHOL_FREQ_OPTIONS = [
  { value: 1, label: "전혀 안 마심" },
  { value: 2, label: "월 1회 미만" },
  { value: 3, label: "월 1회" },
  { value: 4, label: "월 2~4회" },
  { value: 5, label: "주 2~3회" },
  { value: 6, label: "주 4회 이상" },
];

/* 음주량 옵션 */
const ALCOHOL_CUP_OPTIONS = [
  { value: 1, label: "1~2잔" },
  { value: 2, label: "3~4잔" },
  { value: 3, label: "5~6잔" },
  { value: 4, label: "7~9잔" },
  { value: 5, label: "10잔 이상" },
];

/* 채소/과일 빈도 */
const VEG_FRUIT_OPTIONS = [
  { value: 1, label: "하루 3회 이상" },
  { value: 2, label: "하루 2회" },
  { value: 3, label: "하루 1회" },
  { value: 4, label: "주 5~6회" },
  { value: 5, label: "주 2~4회" },
  { value: 6, label: "주 1회" },
  { value: 7, label: "월 2~3회" },
  { value: 8, label: "월 1회" },
  { value: 9, label: "거의 안 먹음" },
];

/* 외식 빈도 */
const OUT_MEAL_OPTIONS = [
  { value: 1, label: "하루 2회 이상" },
  { value: 2, label: "하루 1회" },
  { value: 3, label: "주 5~6회" },
  { value: 4, label: "주 3~4회" },
  { value: 5, label: "주 1~2회" },
  { value: 6, label: "월 1~3회" },
  { value: 7, label: "거의 안 함" },
];

/* 아침식사 빈도 */
const BREAKFAST_OPTIONS = [
  { value: 1, label: "주 5~7회" },
  { value: 2, label: "주 3~4회" },
  { value: 3, label: "주 1~2회" },
  { value: 4, label: "거의 안 함" },
];

/* 흡연 UI → current_smoker / smoking_risk 변환 */
type SmokingChoice = "CURRENT" | "QUIT" | "NEVER";
function smokingToFields(choice: SmokingChoice) {
  if (choice === "CURRENT") return { current_smoker: 1, smoking_risk: 1.0 };
  if (choice === "QUIT") return { current_smoker: 0, smoking_risk: 0.5 };
  return { current_smoker: 0, smoking_risk: 0.0 };
}

function toNum(s: string): number | undefined {
  if (s.trim() === "") return undefined;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : undefined;
}
function toInt(s: string): number | undefined {
  if (s.trim() === "") return undefined;
  const n = parseInt(s, 10);
  return Number.isFinite(n) ? n : undefined;
}

/* ── 메인 페이지 ──────────────────────────── */

export default function HealthRecordsCompletePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const { data: completeness, isLoading: completenessLoading } = useProfileCompleteness();
  const { data: me } = useMe();
  const createProfile = useCreateProfile();
  const createRecord = useCreateHealthRecord();

  const gender = me?.gender;
  const missingFields = completeness?.missing_fields ?? [];

  /* 기존 프로필 prefill */
  const [existingProfile, setExistingProfile] = useState<HealthProfileDetail | null>(null);
  useEffect(() => {
    fetchHealthProfileDetail().then((profile) => {
      if (profile) setExistingProfile(profile);
    });
  }, []);

  /* ── 폼 상태 (누락 필드만 활성) ─── */

  /* 신체계측 */
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [waistCm, setWaistCm] = useState("");

  /* 혈압/혈당 */
  const [systolic, setSystolic] = useState("");
  const [diastolic, setDiastolic] = useState("");
  const [fastingGlucose, setFastingGlucose] = useState("");
  const [bpEnv, setBpEnv] = useState<"HOME" | "HOSPITAL">("HOME");

  /* 가족력 */
  const [familyDm, setFamilyDm] = useState<number | null>(null);
  const [familyHp, setFamilyHp] = useState<number | null>(null);
  const [familyHl, setFamilyHl] = useState<number | null>(null);

  /* 흡연/음주 */
  const [smokingChoice, setSmokingChoice] = useState<SmokingChoice | null>(null);
  const [alcoholFreqY, setAlcoholFreqY] = useState<number | null>(null);
  const [alcoholCup, setAlcoholCup] = useState<number | null>(null);

  /* 수면/운동/수분 */
  const [sleepWeekday, setSleepWeekday] = useState("");
  const [sleepWeekend, setSleepWeekend] = useState("");
  const [modExercise, setModExercise] = useState("");
  const [midActDay, setMidActDay] = useState("");
  const [walkDay, setWalkDay] = useState("");
  const [waterCount, setWaterCount] = useState("");

  /* 식습관 */
  const [vegFreq, setVegFreq] = useState<number | null>(null);
  const [fruitFreq, setFruitFreq] = useState<number | null>(null);
  const [outMealFreq, setOutMealFreq] = useState<number | null>(null);
  const [breakfastFreq, setBreakfastFreq] = useState<number | null>(null);

  /* 추가정보 */
  const [anemia, setAnemia] = useState<number | null>(null);
  const [menopause, setMenopause] = useState<number | null>(null);
  const [ocpTaking, setOcpTaking] = useState<boolean | null>(null);
  const [ocpMonths, setOcpMonths] = useState("");

  /* prefill 기존 값 */
  useEffect(() => {
    if (!existingProfile) return;
    const p = existingProfile;
    if (p.height_cm) setHeightCm(String(p.height_cm));
    if (p.weight_kg) setWeightKg(String(p.weight_kg));
    if (p.waist_cm) setWaistCm(String(p.waist_cm));
    if (p.systolic_bp) setSystolic(String(p.systolic_bp));
    if (p.diastolic_bp) setDiastolic(String(p.diastolic_bp));
    if (p.fasting_blood_sugar) setFastingGlucose(String(p.fasting_blood_sugar));
    if (p.family_dm !== undefined && p.family_dm !== null) setFamilyDm(p.family_dm);
    if (p.family_hp !== undefined && p.family_hp !== null) setFamilyHp(p.family_hp);
    if (p.family_hl !== undefined && p.family_hl !== null) setFamilyHl(p.family_hl);
    if (p.alcohol_freq_y !== undefined && p.alcohol_freq_y !== null) setAlcoholFreqY(p.alcohol_freq_y);
    if (p.alcohol_cup !== undefined && p.alcohol_cup !== null) setAlcoholCup(p.alcohol_cup);
    if (p.sleep_weekday) setSleepWeekday(String(p.sleep_weekday));
    if (p.sleep_weekend) setSleepWeekend(String(p.sleep_weekend));
    if (p.moderate_exercise_hour) setModExercise(String(p.moderate_exercise_hour));
    if (p.mid_act_day) setMidActDay(String(p.mid_act_day));
    if (p.walk_day) setWalkDay(String(p.walk_day));
    if (p.water_count) setWaterCount(String(p.water_count));
    if (p.veg_freq_1 !== undefined && p.veg_freq_1 !== null) setVegFreq(p.veg_freq_1);
    if (p.fruit_freq !== undefined && p.fruit_freq !== null) setFruitFreq(p.fruit_freq);
    if (p.out_meal_freq !== undefined && p.out_meal_freq !== null) setOutMealFreq(p.out_meal_freq);
    if (p.breakfast_freq !== undefined && p.breakfast_freq !== null) setBreakfastFreq(p.breakfast_freq);
    if (p.anemia !== undefined && p.anemia !== null) setAnemia(p.anemia);
    if (p.is_menopause !== undefined && p.is_menopause !== null) setMenopause(p.is_menopause);
    if (p.current_smoker !== undefined) {
      if (p.current_smoker === 1) setSmokingChoice("CURRENT");
      else if (p.smoking_risk !== undefined && p.smoking_risk !== null && p.smoking_risk > 0) setSmokingChoice("QUIT");
      else setSmokingChoice("NEVER");
    }
  }, [existingProfile]);

  /* ── 활성 그룹 계산 ─── */
  const activeGroups = Array.from(
    new Set(missingFields.map((f) => FIELD_TO_GROUP[f]).filter(Boolean))
  ) as FieldGroup[];

  const has = (field: string) => missingFields.includes(field);
  const hasGroup = (group: FieldGroup) => activeGroups.includes(group);

  /* ── 저장 ─────────────────────────────── */

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    const patch: HealthProfileUpsertRequest = {};

    /* 신체계측 */
    if (has("height_cm")) { const v = toNum(heightCm); if (v !== undefined) patch.height_cm = v; }
    if (has("weight_kg")) { const v = toNum(weightKg); if (v !== undefined) patch.weight_kg = v; }
    if (has("waist_cm")) { const v = toNum(waistCm); if (v !== undefined) patch.waist_cm = v; }

    /* 혈압/혈당 */
    if (has("systolic_bp")) { const v = toNum(systolic); if (v !== undefined) patch.systolic_bp = v; }
    if (has("diastolic_bp")) { const v = toNum(diastolic); if (v !== undefined) patch.diastolic_bp = v; }
    if (has("fasting_blood_sugar")) { const v = toNum(fastingGlucose); if (v !== undefined) patch.fasting_blood_sugar = v; }
    if (has("systolic_bp") || has("diastolic_bp")) patch.bp_measure_env = bpEnv;

    /* 가족력 */
    if (has("family_dm") && familyDm !== null) patch.family_dm = familyDm;
    if (has("family_hp") && familyHp !== null) patch.family_hp = familyHp;
    if (has("family_hl") && familyHl !== null) patch.family_hl = familyHl;

    /* 흡연/음주 */
    if ((has("smoking_risk") || has("current_smoker")) && smokingChoice !== null) {
      const { current_smoker, smoking_risk } = smokingToFields(smokingChoice);
      patch.current_smoker = current_smoker;
      patch.smoking_risk = smoking_risk;
    }
    if (has("alcohol_freq_y") && alcoholFreqY !== null) {
      patch.alcohol_freq_y = alcoholFreqY;
      if (alcoholFreqY !== 1 && has("alcohol_cup") && alcoholCup !== null) {
        patch.alcohol_cup = alcoholCup;
      }
    }

    /* 수면/운동/수분 */
    if (has("sleep_weekday")) { const v = toNum(sleepWeekday); if (v !== undefined) patch.sleep_weekday = v; }
    if (has("sleep_weekend")) { const v = toNum(sleepWeekend); if (v !== undefined) patch.sleep_weekend = v; }
    if (has("moderate_exercise_hour")) { const v = toNum(modExercise); if (v !== undefined) patch.moderate_exercise_hour = v; }
    if (has("mid_act_day")) { const v = toInt(midActDay); if (v !== undefined) patch.mid_act_day = v; }
    if (has("walk_day")) { const v = toInt(walkDay); if (v !== undefined) patch.walk_day = v; }
    if (has("water_count")) { const v = toInt(waterCount); if (v !== undefined) patch.water_count = v; }

    /* 식습관 */
    if (has("veg_freq_1") && vegFreq !== null) patch.veg_freq_1 = vegFreq;
    if (has("fruit_freq") && fruitFreq !== null) patch.fruit_freq = fruitFreq;
    if (has("out_meal_freq") && outMealFreq !== null) patch.out_meal_freq = outMealFreq;
    if (has("breakfast_freq") && breakfastFreq !== null) patch.breakfast_freq = breakfastFreq;

    /* 추가정보 */
    if (has("anemia") && anemia !== null) patch.anemia = anemia;
    if (has("is_menopause") && menopause !== null) patch.is_menopause = menopause;
    if (has("ocp_total_months") && gender === "FEMALE") {
      if (ocpTaking === true) patch.ocp_total_months = toInt(ocpMonths) ?? 0;
      else if (ocpTaking === false) patch.ocp_total_months = 0;
    }

    if (Object.keys(patch).length === 0) {
      showToast("입력된 값이 없습니다.", "warning");
      return;
    }

    try {
      await createProfile.mutateAsync(patch);

      /* 시계열 기록 (체중, 허리둘레, 혈압, 혈당) */
      const now = format(new Date(), "yyyy-MM-dd'T'HH:mm:ssxxx");
      const timeRecords: Promise<unknown>[] = [];
      if (patch.weight_kg !== undefined) {
        timeRecords.push(createRecord.mutateAsync({ record_type: "WEIGHT", primary_value: patch.weight_kg, unit: "kg", measured_at: now }));
      }
      if (patch.waist_cm !== undefined) {
        timeRecords.push(createRecord.mutateAsync({ record_type: "WAIST", primary_value: patch.waist_cm, unit: "cm", measured_at: now }));
      }
      if (patch.systolic_bp !== undefined && patch.diastolic_bp !== undefined) {
        timeRecords.push(createRecord.mutateAsync({ record_type: "BLOOD_PRESSURE", sub_type: bpEnv, primary_value: patch.systolic_bp, secondary_value: patch.diastolic_bp, unit: "mmHg", measured_at: now }));
      }
      if (patch.fasting_blood_sugar !== undefined) {
        timeRecords.push(createRecord.mutateAsync({ record_type: "BLOOD_GLUCOSE", sub_type: "FASTING", primary_value: patch.fasting_blood_sugar, unit: "mg/dL", measured_at: now }));
      }
      await Promise.allSettled(timeRecords);

      /* completeness 재조회 */
      await queryClient.invalidateQueries({ queryKey: PROFILE_COMPLETENESS_KEY });
      const fresh = await queryClient.fetchQuery({
        queryKey: PROFILE_COMPLETENESS_KEY,
        queryFn: () => import("@/lib/api/health").then((m) => m.fetchProfileCompleteness()),
        staleTime: 0,
      });

      if (fresh?.complete) {
        showToast("모든 항목이 입력되었습니다. 위험도 예측이 가능합니다.", "success");
        router.push("/health-records?tab=risk");
      } else {
        const remaining = fresh?.missing_fields.length ?? 0;
        showToast(`저장 완료. 아직 ${remaining}개 항목이 남았습니다.`, "success");
      }
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  const isLoading = createProfile.isPending || createRecord.isPending;

  /* ── 로딩 ── */
  if (completenessLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface rounded-[12px] w-1/2" />
          <div className="h-40 bg-surface rounded-[16px]" />
        </div>
      </div>
    );
  }

  /* ── 이미 완성 ── */
  if (completeness?.complete) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6 text-center space-y-3">
        <p className="text-4xl" aria-hidden="true">✅</p>
        <p className="font-bold text-text-primary text-lg">모든 건강 데이터가 입력되어 있어요!</p>
        <p className="text-sm text-text-secondary">위험도 탭에서 예측을 실행해 보세요.</p>
        <button
          type="button"
          onClick={() => router.push("/health-records?tab=risk")}
          className="inline-flex items-center gap-1 mt-2 px-5 py-2.5 bg-brand text-brand-black font-semibold rounded-[12px] text-sm hover:bg-brand-hover transition-colors"
        >
          위험도 탭으로 이동 →
        </button>
      </div>
    );
  }

  /* ── 폼 ── */
  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* 헤더 */}
      <div className="mb-6">
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm text-text-secondary hover:text-text-primary flex items-center gap-1 mb-3"
        >
          ← 뒤로
        </button>
        <h1 className="text-xl font-black text-text-primary">누락 항목 입력</h1>
        <p className="text-sm text-text-secondary mt-1">
          위험도 예측에 필요한 항목을 입력해 주세요. 이미 입력한 값은 다시 입력하지 않아도 됩니다.
        </p>
      </div>

      {/* 현재 완성도 표시 */}
      {completeness && (
        <div className="mb-5 bg-white rounded-[16px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.07)]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-text-primary">입력 완성도</span>
            <span className="text-sm font-bold text-text-primary">{completeness.percent}%</span>
          </div>
          <div className="h-2.5 bg-surface rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-black rounded-full transition-all duration-500"
              style={{ width: `${completeness.percent}%` }}
              role="progressbar"
              aria-valuenow={completeness.percent}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <p className="text-xs text-text-tertiary mt-1.5">
            {completeness.filled}/{completeness.total} 항목 입력됨 · 누락 {missingFields.length}개
          </p>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-5">

        {/* 신체계측 */}
        {hasGroup("measure") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.measure}</h2>
            <div className="grid grid-cols-2 gap-4">
              {has("height_cm") && (
                <NumberInput label="키" id="height_cm" unit="cm" placeholder="170" value={heightCm} onChange={setHeightCm} />
              )}
              {has("weight_kg") && (
                <NumberInput label="몸무게" id="weight_kg" unit="kg" placeholder="65" value={weightKg} onChange={setWeightKg} />
              )}
            </div>
            {has("waist_cm") && (
              <NumberInput label="허리둘레" id="waist_cm" unit="cm" placeholder="80" value={waistCm} onChange={setWaistCm} />
            )}
          </div>
        )}

        {/* 혈압/혈당 */}
        {hasGroup("vitals") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.vitals}</h2>
            {(has("systolic_bp") || has("diastolic_bp")) && (
              <div>
                <p className="text-sm font-medium text-text-primary mb-2">혈압 측정 환경</p>
                <div className="flex gap-2 mb-3">
                  {(["HOME", "HOSPITAL"] as const).map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setBpEnv(v)}
                      className={[
                        "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
                        bpEnv === v ? "bg-brand-black text-white border-brand-black" : "bg-white text-text-secondary border-border",
                      ].join(" ")}
                    >
                      {v === "HOME" ? "가정" : "병원"}
                    </button>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {has("systolic_bp") && (
                    <NumberInput label="수축기" id="systolic_bp" unit="mmHg" placeholder="120" value={systolic} onChange={setSystolic} />
                  )}
                  {has("diastolic_bp") && (
                    <NumberInput label="이완기" id="diastolic_bp" unit="mmHg" placeholder="80" value={diastolic} onChange={setDiastolic} />
                  )}
                </div>
              </div>
            )}
            {has("fasting_blood_sugar") && (
              <NumberInput label="공복혈당" id="fasting_blood_sugar" unit="mg/dL" placeholder="100" value={fastingGlucose} onChange={setFastingGlucose} />
            )}
          </div>
        )}

        {/* 가족력 */}
        {hasGroup("family") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.family}</h2>
            {has("family_dm") && (
              <TriChip label="당뇨 가족력" options={[{ value: 1, label: "있음" }, { value: 0, label: "없음" }, { value: -1, label: "모름" }]} value={familyDm} onChange={setFamilyDm} />
            )}
            {has("family_hp") && (
              <TriChip label="고혈압 가족력" options={[{ value: 1, label: "있음" }, { value: 0, label: "없음" }, { value: -1, label: "모름" }]} value={familyHp} onChange={setFamilyHp} />
            )}
            {has("family_hl") && (
              <TriChip label="고지혈증 가족력" options={[{ value: 1, label: "있음" }, { value: 0, label: "없음" }, { value: -1, label: "모름" }]} value={familyHl} onChange={setFamilyHl} />
            )}
          </div>
        )}

        {/* 흡연/음주 */}
        {hasGroup("smoking") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.smoking}</h2>
            {(has("smoking_risk") || has("current_smoker")) && (
              <div>
                <p className="text-sm font-medium text-text-primary mb-2">흡연 여부</p>
                <div className="flex flex-col gap-2">
                  {([
                    { value: "CURRENT" as const, label: "현재 흡연 중" },
                    { value: "QUIT" as const, label: "과거 흡연, 현재 아님" },
                    { value: "NEVER" as const, label: "한 번도 피운 적 없음" },
                  ]).map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setSmokingChoice(opt.value)}
                      className={[
                        "w-full py-2.5 text-sm rounded-[10px] border transition-colors min-h-[44px] text-left px-4",
                        smokingChoice === opt.value
                          ? "bg-brand-black text-white border-brand-black"
                          : "bg-white text-text-secondary border-border hover:border-text-primary",
                      ].join(" ")}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {has("alcohol_freq_y") && (
              <SelectChip label="음주 빈도" options={ALCOHOL_FREQ_OPTIONS} value={alcoholFreqY} onChange={setAlcoholFreqY} />
            )}
            {has("alcohol_cup") && alcoholFreqY !== 1 && (
              <SelectChip label="1회 평균 음주량" options={ALCOHOL_CUP_OPTIONS} value={alcoholCup} onChange={setAlcoholCup} />
            )}
          </div>
        )}

        {/* 수면/운동/수분 */}
        {hasGroup("activity") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.activity}</h2>
            <div className="grid grid-cols-2 gap-4">
              {has("sleep_weekday") && (
                <NumberInput label="주중 수면시간" id="sleep_weekday" unit="시간" placeholder="7" value={sleepWeekday} onChange={setSleepWeekday} />
              )}
              {has("sleep_weekend") && (
                <NumberInput label="주말 수면시간" id="sleep_weekend" unit="시간" placeholder="8" value={sleepWeekend} onChange={setSleepWeekend} />
              )}
              {has("moderate_exercise_hour") && (
                <NumberInput label="중강도 운동" id="moderate_exercise_hour" unit="시간/주" placeholder="2.5" value={modExercise} onChange={setModExercise} />
              )}
              {has("mid_act_day") && (
                <NumberInput label="중간 활동 일수" id="mid_act_day" unit="일/주" placeholder="3" value={midActDay} onChange={setMidActDay} />
              )}
              {has("walk_day") && (
                <NumberInput label="걷기 일수" id="walk_day" unit="일/주" placeholder="5" value={walkDay} onChange={setWalkDay} />
              )}
              {has("water_count") && (
                <NumberInput label="하루 물 섭취량" id="water_count" unit="잔" placeholder="8" value={waterCount} onChange={setWaterCount} />
              )}
            </div>
          </div>
        )}

        {/* 식습관 */}
        {hasGroup("diet") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.diet}</h2>
            {has("veg_freq_1") && (
              <SelectChip label="채소 섭취 빈도" options={VEG_FRUIT_OPTIONS} value={vegFreq} onChange={setVegFreq} />
            )}
            {has("fruit_freq") && (
              <SelectChip label="과일 섭취 빈도" options={VEG_FRUIT_OPTIONS} value={fruitFreq} onChange={setFruitFreq} />
            )}
            {has("out_meal_freq") && (
              <SelectChip label="외식 빈도" options={OUT_MEAL_OPTIONS} value={outMealFreq} onChange={setOutMealFreq} />
            )}
            {has("breakfast_freq") && (
              <SelectChip label="아침 식사 빈도" options={BREAKFAST_OPTIONS} value={breakfastFreq} onChange={setBreakfastFreq} />
            )}
          </div>
        )}

        {/* 추가정보 */}
        {hasGroup("extras") && (
          <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-4">
            <h2 className="font-bold text-lg text-text-primary">{GROUP_LABEL.extras}</h2>
            {has("anemia") && (
              <TriChip label="빈혈 여부" options={[{ value: 1, label: "예" }, { value: 0, label: "아니오" }, { value: -1, label: "모름" }]} value={anemia} onChange={setAnemia} />
            )}
            {has("is_menopause") && gender === "FEMALE" && (
              <TriChip label="폐경 여부" options={[{ value: 1, label: "예" }, { value: 0, label: "아니오" }]} value={menopause} onChange={setMenopause} />
            )}
            {has("ocp_total_months") && gender === "FEMALE" && (
              <div className="space-y-2">
                <TriChip label="호르몬제(경구피임약) 복용 여부" options={[{ value: 1, label: "복용 중" }, { value: 0, label: "아니오" }]} value={ocpTaking === null ? null : ocpTaking ? 1 : 0} onChange={(v) => setOcpTaking(v === 1)} />
                {ocpTaking === true && (
                  <NumberInput label="복용 기간" id="ocp_months" unit="개월" placeholder="12" value={ocpMonths} onChange={setOcpMonths} />
                )}
              </div>
            )}
          </div>
        )}

        <Button type="submit" fullWidth loading={isLoading}>
          저장하기
        </Button>
      </form>
    </div>
  );
}
