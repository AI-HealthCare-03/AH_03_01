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
  | "profile";

export type SubType =
  | "HOME"
  | "HOSPITAL"
  | "FASTING"
  | "POSTMEAL"
  | null;

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

export type SmokingStatus = "NEVER" | "CURRENT" | "QUIT";
export type AlcoholFrequency = "NONE" | "WEEKLY_1_2" | "WEEKLY_3_4" | "DAILY";
export type PregnancyStatus = "NONE" | "PREGNANT" | "POSTPARTUM";
export type ChronicDisease =
  | "HYPERTENSION"
  | "DIABETES"
  | "HYPERLIPIDEMIA"
  | "HEART_DISEASE"
  | "KIDNEY_DISEASE"
  | "OBESITY"
  | "NONE";

/** 건강 프로필 Upsert 요청 */
export interface HealthProfileUpsertRequest {
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  smoking_status?: SmokingStatus;
  alcohol_frequency?: AlcoholFrequency;
  family_history_diabetes?: boolean;
  family_history_hypertension?: boolean;
  chronic_diseases?: ChronicDisease[];
  pregnancy_status?: PregnancyStatus;
}

/** 건강 프로필 상세 응답 */
export interface HealthProfileDetail {
  id?: number;
  record_type?: "profile";
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  smoking_status?: SmokingStatus;
  alcohol_frequency?: AlcoholFrequency;
  family_history_diabetes?: boolean;
  family_history_hypertension?: boolean;
  chronic_diseases?: ChronicDisease[];
  pregnancy_status?: PregnancyStatus;
  /* 백엔드 HealthProfileResponse 는 updated_at 만 보냄. 호환을 위해 recorded_at 옵셔널 보존 */
  updated_at?: string;
  recorded_at?: string;
}

/* ── 통계 / 추이 ────────────────────────────── */

export type StatPeriod = "1w" | "1m" | "3m" | "6m";

export interface StatSeriesPoint {
  measured_at: string;
  primary_value: string;  /* Decimal → string */
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

/* ── 예측 ────────────────────────────────────── */

export interface ContributingFactor {
  factor: string;
  weight: number;
  description?: string;
}

export interface PredictionDetail {
  id: number;
  disease_type: DiseaseType;
  risk_score: number;
  risk_level: "NORMAL" | "CAUTION" | "RISK" | "HIGH_RISK";
  risk_grade: RiskGrade;
  contributing_factors: ContributingFactor[];
  disclaimer?: string;
  created_at: string;
}

export interface PredictionDetailResponse {
  items: PredictionDetail[];
}

/* ── 권고사항 ─────────────────────────────── */

export type RecommendationCategory = "EXERCISE" | "DIET" | "SMOKING" | "SLEEP" | "GENERAL";

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
  disease_risk_summary: Record<string, DiseaseRiskSummaryEntry>; /* keys: HYPERTENSION|DIABETES|CARDIOVASCULAR */
  health_data_summary: Record<string, unknown>;
  challenge_summary: Record<string, unknown> & Partial<ChallengeSummary>;
  pdf_url: string | null;
  generated_at: string;
  /* contributing_factors_top3 와 coaching_message 는 백엔드 응답에 없음.
     컴포넌트가 별도 prediction 응답에서 도출하거나 정적 fallback 사용. */
  coaching_message?: string;
}

/* ── 위저드 폼 상태 ─────────────────────── */

export interface WizardFormStep1 {
  height_cm: string;
  weight_kg: string;
  waist_cm: string;
  smoking_status: SmokingStatus;
  alcohol_frequency: AlcoholFrequency;
  family_history_diabetes: boolean;
  family_history_hypertension: boolean;
  chronic_diseases: ChronicDisease[];
  pregnancy_status: PregnancyStatus;
}

export interface WizardFormStep2 {
  systolic: string;
  diastolic: string;
  measurement_env: "HOME" | "HOSPITAL";
}

export interface WizardFormStep3 {
  fasting_glucose: string;
  postmeal_glucose: string;
  hba1c: string;
}
