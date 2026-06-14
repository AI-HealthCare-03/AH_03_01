/* =========================================
   건강·위험도 도메인 타입 정의
   ========================================= */

import type { DiseaseType, RiskGrade } from "./api";

/* ── 건강 기록 ─────────────────────────────── */

export type RecordType =
  | "BLOOD_PRESSURE"
  | "BLOOD_GLUCOSE"
  | "HBA1C"
  | "WEIGHT"
  | "WAIST"
  | "profile";

export type SubType = "HOME" | "HOSPITAL" | "FASTING" | "POSTMEAL" | null;

/** 건강 기록 생성 요청 */
export interface CreateHealthRecordRequest {
  record_type: RecordType;
  sub_type?: string;
  primary_value: number;
  secondary_value?: number;
  unit: string;
  measured_at: string; /* ISO datetime */
}

/** 건강 기록 아이템 */
export interface HealthRecordItem {
  id: number;
  record_type: RecordType;
  sub_type?: string | null;
  primary_value: string; /* Decimal → string */
  secondary_value?: string | null;
  unit: string;
  measured_at: string;
  created_at: string;
}

/* ── 건강 프로필 (상세) ────────────────────── */

/** v1 호환용 — 외부 컴포넌트가 import 하는 경우를 위해 유지 (내부 사용 금지) */
export type SmokingStatus = "NEVER" | "CURRENT" | "QUIT";
/** v1 호환용 */
export type AlcoholFrequency = "NONE" | "WEEKLY_1_2" | "WEEKLY_3_4" | "DAILY";
/** v1 호환용 */
export type PregnancyStatus = "NONE" | "PREGNANT" | "POSTPARTUM";
export type ChronicDisease =
  | "HYPERTENSION"
  | "DIABETES"
  | "HYPERLIPIDEMIA"
  | "HEART_DISEASE"
  | "KIDNEY_DISEASE"
  | "OBESITY"
  | "NONE";

/** 건강 프로필 Upsert 요청 — v2 (28필드, 백엔드 HealthProfileUpsertRequest 와 1:1 매핑) */
export interface HealthProfileUpsertRequest {
  /* 신체계측 */
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  /* 혈압 / 혈당 (프로필 저장용) */
  systolic_bp?: number;
  diastolic_bp?: number;
  fasting_blood_sugar?: number;
  /* 수면 */
  sleep_weekday?: number;
  sleep_weekend?: number;
  /* 운동 */
  moderate_exercise_hour?: number;
  mid_act_day?: number;
  walk_day?: number;
  /* 수분 */
  water_count?: number;
  /* 가족력 (1=있음 / 0=없음 / -1=모름) */
  family_dm?: number;
  family_hp?: number;
  family_hl?: number;
  /* 흡연 */
  current_smoker?: number;
  smoking_risk?: number;
  /* 음주 */
  alcohol_freq_y?: number;
  alcohol_cup?: number;
  /* 식습관 */
  veg_freq_1?: number;
  fruit_freq?: number;
  out_meal_freq?: number;
  breakfast_freq?: number;
  /* 여성 전용 */
  is_menopause?: number;
  ocp_total_months?: number;
  /* 기타 */
  anemia?: number;
  /* 예측 미사용 / 챗봇용 */
  chronic_diseases?: string[];
  pregnancy_status?: "NOT_APPLICABLE" | "PREGNANT" | "POSTPARTUM";
  bp_measure_env?: "HOME" | "HOSPITAL";
}

/** 건강 프로필 상세 응답.
 *
 * 백엔드 v2 응답 키를 기준으로 정의한다.
 * 기존 컴포넌트(DetailTab 등)가 참조하는 구 키도 옵셔널로 유지해 호환성을 보존한다.
 */
export interface HealthProfileDetail {
  id?: number;
  record_type?: "profile";
  /* 신체계측 */
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  /* 혈압 / 혈당 */
  systolic_bp?: number;
  diastolic_bp?: number;
  fasting_blood_sugar?: number;
  /* 수면 */
  sleep_weekday?: number;
  sleep_weekend?: number;
  /* 운동 */
  moderate_exercise_hour?: number;
  mid_act_day?: number;
  walk_day?: number;
  /* 수분 */
  water_count?: number;
  /* 가족력 */
  family_dm?: number;
  family_hp?: number;
  family_hl?: number;
  /* 흡연 */
  current_smoker?: number;
  smoking_risk?: number;
  /* 음주 */
  alcohol_freq_y?: number;
  alcohol_cup?: number;
  /* 식습관 */
  veg_freq_1?: number;
  fruit_freq?: number;
  out_meal_freq?: number;
  breakfast_freq?: number;
  /* 여성 전용 */
  is_menopause?: number;
  ocp_total_months?: number;
  /* 기타 */
  anemia?: number;
  /* 예측 미사용 / 챗봇용 */
  chronic_diseases?: string[];
  pregnancy_status?: string;
  bp_measure_env?: "HOME" | "HOSPITAL";
  medications?: string[];
  /* v1 호환 키 (DetailTab 등 외부 컴포넌트가 참조) */
  has_diabetes_family_history?: boolean;
  has_hypertension_family_history?: boolean;
  is_smoker?: boolean;
  alcohol_intake?: string;
  pregnancy_history?: string;
  is_chronic_patient?: boolean;
  diseases?: string[];
  updated_at?: string;
  recorded_at?: string;
}

/* ── 통계 / 추이 ────────────────────────────── */

export type StatPeriod = "1w" | "1m" | "3m" | "6m";

export interface StatSeriesPoint {
  measured_at: string;
  primary_value: string; /* Decimal → string */
  secondary_value?: string | null;
  sub_type?: string | null;
  level?: string | null;
}

export interface HealthStatisticsResponse {
  metric: string;
  period?: string;
  series: StatSeriesPoint[];
  data_count: number;
  insufficient_data: boolean;
  reference_range?: {
    normal_max?: number;
    caution_max?: number;
  };
  peer_average?: {
    primary_value: number;
    secondary_value?: number;
    label: string;
  } | null;
}

/* ── 프로필 완성도 ──────────────────────────── */

export interface ProfileCompleteness {
  percent: number;
  filled: number;
  total: number;
  missing_fields: string[];
  complete: boolean;
}

/* completeness 가 포함된 프로필 응답 */
export interface HealthProfileWithCompleteness extends HealthProfileDetail {
  completeness?: ProfileCompleteness;
}

/* ── 예측 ────────────────────────────────────── */

export interface ContributingFactor {
  factor: string;
  weight: number;
  description?: string;
  name_kor?: string;
  direction?: string;
}

export interface PredictionDetail {
  id: number;
  disease_type: DiseaseType;
  risk_score: number;
  risk_level: "NORMAL" | "CAUTION" | "RISK" | "HIGH_RISK";
  risk_grade: RiskGrade;
  /** risk_score 기반 5단계 한글 라벨. "매우 낮음"|"낮음"|"보통"|"높음"|"매우 높음" */
  risk_level_label?: string;
  contributing_factors: ContributingFactor[];
  disclaimer?: string;
  created_at: string;
}

export interface PredictionDetailResponse {
  items: PredictionDetail[];
}

/* ── 권고사항 ─────────────────────────────── */

export type RecommendationCategory =
  | "EXERCISE"
  | "DIET"
  | "SMOKING"
  | "SLEEP"
  | "GENERAL";

export interface RiskRecommendation {
  id?: number;
  category: RecommendationCategory | string;
  title?: string;
  content: string;
  priority?: number;
}

export interface RiskRecommendationResponse {
  prediction_id: number;
  risk_level: string;
  recommendations: RiskRecommendation[];
  disclaimer?: string;
}

/* ── RAG 위험도 권고 (POST /api/v1/risk-recommendations) ─── */

export interface RagPredictionItem {
  disease_type: DiseaseType;
  risk_score: number;
  risk_level: "NORMAL" | "CAUTION" | "RISK" | "HIGH_RISK";
  contributing_factors: ContributingFactor[];
}

export interface RagSource {
  title?: string;
  document_id?: string;
  snippet?: string;
  source?: string;
}

export interface RecommendedChallengeItem {
  template_id: number;
  title: string;
  category: string;
  difficulty: string;
  reason: string;
  priority: "TOP" | "RECOMMENDED" | "OPTIONAL" | null;
}

export interface RagRiskRecommendationResponse {
  answer: string;
  predictions: RagPredictionItem[];
  sources: RagSource[];
  recommended_tips: string[];
  recommended_diet: string[];
  recommended_challenges?: RecommendedChallengeItem[];
  has_required_data: boolean;
  missing_fields: string[];
  action_hint: "navigate_to_health_info" | null;
  is_fallback: boolean;
  eval_revision_count: number | null;
  disclaimer: string;
  model_version: string;
}

/* ── 월간 리포트 ─────────────────────────── */

export interface ChallengeSummaryItem {
  id: number;
  title: string;
  category: string;
  progress_rate: number; /* 0~100 */
  status: "ACTIVE" | "COMPLETED" | "CANCELLED" | "FAILED";
}

export interface ChallengeSummary {
  participated: number;
  succeeded: number;
  failed: number;
  in_progress: number;
  items: ChallengeSummaryItem[];
}

export interface MonthlyMiniStat {
  label: string;
  value: string;
}

/* 백엔드 실제 응답 (app/services/health.py::MonthlyReportService) */
export interface DiseaseRiskSummaryEntry {
  risk_score: number | string;
  risk_level: string; /* NORMAL|CAUTION|RISK|HIGH_RISK */
  calculated_at?: string;
}

export interface MonthlyReportResponse {
  year_month: string; /* YYYY-MM */
  disease_risk_summary: Record<
    string,
    DiseaseRiskSummaryEntry
  >; /* keys: HYPERTENSION|DIABETES|CARDIOVASCULAR */
  health_data_summary: Record<string, unknown>;
  challenge_summary: Record<string, unknown> & Partial<ChallengeSummary>;
  pdf_url: string | null;
  generated_at: string;
  /* contributing_factors_top3 와 coaching_message 는 백엔드 응답에 없음.
     컴포넌트가 별도 prediction 응답에서 도출하거나 정적 fallback 사용. */
  coaching_message?: string;
}

/* ── 위저드 폼 상태 (v2) ─────────────────── */

/** Step 1: 신체계측 */
export interface WizardFormStep1 {
  height_cm: string;
  weight_kg: string;
  waist_cm: string;
}

/** Step 2: 혈압·혈당 (측정값) */
export interface WizardFormStep2 {
  systolic: string;
  diastolic: string;
  measurement_env: "HOME" | "HOSPITAL";
  fasting_glucose: string;
}

/** Step 3: 가족력 */
export interface WizardFormStep3 {
  family_dm: number; /* 1=있음 / 0=없음 / -1=모름 */
  family_hp: number;
  family_hl: number;
}

/** Step 4: 흡연·음주 */
export interface WizardFormStep4 {
  /* 흡연 UI 선택값 */
  smoking_choice: "CURRENT" | "QUIT" | "NEVER";
  /* 음주 */
  alcohol_freq_y: number | null; /* null = 미선택 */
  alcohol_cup: number | null;
}

/** Step 5: 수면·운동·수분 */
export interface WizardFormStep5 {
  sleep_weekday: string;
  sleep_weekend: string;
  moderate_exercise_hour: string;
  mid_act_day: string;
  walk_day: string;
  water_count: string;
}

/** Step 6: 식습관 */
export interface WizardFormStep6 {
  veg_freq_1: number | null;
  fruit_freq: number | null;
  out_meal_freq: number | null;
  breakfast_freq: number | null;
}

/** Step 7: 여성전용·빈혈·추가정보 */
export interface WizardFormStep7 {
  is_menopause: number | null; /* 1=예 / 0=아니오 / null=스킵(남성) */
  ocp_taking: boolean | null; /* UI 선택. null=스킵(남성) */
  ocp_total_months: string; /* ocp_taking=true 일 때만 유효 */
  anemia: number | null; /* 1=예 / 0=아니오 / null=모름(미전송) */
  chronic_diseases: string[];
  pregnancy_status: "NOT_APPLICABLE" | "PREGNANT" | "POSTPARTUM";
}
