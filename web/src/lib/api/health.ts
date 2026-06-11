/* =========================================
   건강·위험도 도메인 API 호출 함수
   /api/v1/ prefix 기반 apiClient 사용
   ========================================= */

import apiClient from "./client";
import type {
  CreateHealthRecordRequest,
  HealthRecordItem,
  HealthProfileUpsertRequest,
  HealthProfileDetail,
  HealthStatisticsResponse,
  StatPeriod,
  PredictionDetail,
  PredictionDetailResponse,
  RiskRecommendationResponse,
  MonthlyReportResponse,
} from "@/types/health";
import type { DiseaseType } from "@/types/api";

/* ── 건강 기록 목록 ───────────────────────── */

export async function fetchHealthRecordList(params: {
  recordType?: string;
  subType?: string;
  from?: string;
  to?: string;
  page?: number;
  size?: number;
}): Promise<HealthRecordItem[]> {
  /* 백엔드 응답: { page, size, total_elements, total_pages, items: HealthRecordItem[] }
     items 배열만 추출해 반환 (정렬은 백엔드가 measured_at DESC 처리). */
  const { data } = await apiClient.get<{ items?: HealthRecordItem[] }>(
    "/api/v1/health-records",
    { params }
  );
  return data?.items ?? [];
}

/* ── 건강 프로필 상세 ─────────────────────── */

export async function fetchHealthProfileDetail(): Promise<HealthProfileDetail | null> {
  try {
    const { data } = await apiClient.get<HealthProfileDetail>(
      "/api/v1/health-records",
      { params: { recordType: "profile" } }
    );
    return data ?? null;
  } catch {
    return null;
  }
}

/* ── 건강 프로필 저장 (upsert) ─────────────── */

export async function upsertHealthProfile(
  body: HealthProfileUpsertRequest
): Promise<HealthProfileDetail> {
  const { data } = await apiClient.post<HealthProfileDetail>(
    "/api/v1/health-records",
    body,
    { params: { recordType: "profile" } }
  );
  return data;
}

/* ── 건강 기록 생성 ─────────────────────── */

export async function createHealthRecord(
  body: CreateHealthRecordRequest
): Promise<HealthRecordItem> {
  const { data } = await apiClient.post<HealthRecordItem>(
    "/api/v1/health-records",
    body
  );
  return data;
}

/* ── 통계 (추이 차트) ────────────────────── */

export async function fetchHealthStatistics(params: {
  metric: string;
  subType?: string;
  period?: StatPeriod;
  limit?: number;
}): Promise<HealthStatisticsResponse | null> {
  try {
    const { data } = await apiClient.get<HealthStatisticsResponse>(
      "/api/v1/health-records/statistics",
      { params }
    );
    return data;
  } catch {
    return null;
  }
}

/* ── 예측 생성 ──────────────────────────── */

export async function createPrediction(
  diseaseType: DiseaseType
): Promise<PredictionDetail> {
  const { data } = await apiClient.post<PredictionDetail>(
    "/api/v1/predictions",
    {},
    { params: { diseaseType } }
  );
  return data;
}

/* ── 예측 목록 ──────────────────────────── */

export async function fetchPredictionsList(params?: {
  latest?: boolean;
  diseaseType?: DiseaseType;
}): Promise<PredictionDetailResponse> {
  const { data } = await apiClient.get<PredictionDetailResponse>(
    "/api/v1/predictions",
    { params }
  );
  return data;
}

/* ── 예측 단건 ──────────────────────────── */

export async function fetchPredictionById(
  id: number
): Promise<PredictionDetail | null> {
  try {
    const { data } = await apiClient.get<PredictionDetail>(
      `/api/v1/predictions/${id}`
    );
    return data;
  } catch {
    return null;
  }
}

/* ── 권고사항 ────────────────────────────── */

export async function fetchRiskRecommendations(
  predictionId: number
): Promise<RiskRecommendationResponse | null> {
  try {
    const { data } = await apiClient.get<RiskRecommendationResponse>(
      `/api/v1/predictions/${predictionId}/risk-recommendations`
    );
    return data;
  } catch {
    return null;
  }
}

/* ── 월간 리포트 ─────────────────────────── */

export async function fetchMonthlyReport(
  month: string /* YYYY-MM */
): Promise<MonthlyReportResponse | null> {
  try {
    const { data } = await apiClient.get<MonthlyReportResponse>(
      "/api/v1/health-reports",
      { params: { period: "monthly", month } }
    );
    return data;
  } catch {
    return null;
  }
}
