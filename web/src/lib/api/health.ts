/* =========================================
   건강·위험도 도메인 API 호출 함수
   /api/v1/ prefix 기반 apiClient 사용
   ========================================= */

import apiClient from "./client";
import { API_BASE_URL, ROUTES } from "@/constants";
import { getToken, removeToken } from "@/lib/tokens";
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
  RagRiskRecommendationResponse,
  MonthlyReportResponse,
  MonthlyReportV2Response,
  ProfileCompleteness,
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

/* ── 프로필 완성도 조회 ─────────────────── */

export async function fetchProfileCompleteness(): Promise<ProfileCompleteness | null> {
  try {
    const { data } = await apiClient.get<{ completeness?: ProfileCompleteness }>(
      "/api/v1/health-records",
      { params: { recordType: "profile" } }
    );
    return data?.completeness ?? null;
  } catch {
    return null;
  }
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

/* ── RAG 위험도 권고 (단일 통합 엔드포인트) ─── */

export async function fetchRagRiskRecommendation(): Promise<RagRiskRecommendationResponse> {
  const { data } = await apiClient.post<RagRiskRecommendationResponse>(
    "/api/v1/risk-recommendations"
  );
  return data;
}

/* ── RAG 위험도 권고 SSE 스트리밍 ──────────── */

export interface StreamRiskCallbacks {
  onMeta?: (payload: { cached: boolean }) => void;
  onStage?: (payload: { node: string; label: string }) => void;
  onToken?: (text: string) => void;
  onDone: (payload: RagRiskRecommendationResponse) => void;
  onError: (message: string) => void;
}

/**
 * POST /api/v1/risk-recommendations/stream 을 SSE 로 소비.
 * meta → stage* → token* → done (실패 시 error). streamChatMessage 와 동일 패턴.
 */
export async function streamRagRiskRecommendation(
  callbacks: StreamRiskCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const url = `${API_BASE_URL}/api/v1/risk-recommendations/stream`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal,
    });
  } catch (err) {
    callbacks.onError(
      err instanceof Error ? err.message : "네트워크 오류가 발생했습니다"
    );
    return;
  }

  if (response.status === 401) {
    removeToken();
    if (typeof window !== "undefined") {
      window.location.href = ROUTES.LOGIN;
    }
    return;
  }

  if (!response.ok || !response.body) {
    let detail = `서버 오류가 발생했습니다 (${response.status})`;
    try {
      const errBody = await response.json();
      if (typeof errBody?.detail === "string") detail = errBody.detail;
    } catch {
      /* ignore */
    }
    callbacks.onError(detail);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processFrame = (frame: string) => {
    let eventType = "";
    let dataStr = "";

    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) {
        eventType = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataStr = line.slice("data:".length).trim();
      }
    }

    if (!eventType || !dataStr) return;

    let parsed: unknown;
    try {
      parsed = JSON.parse(dataStr);
    } catch {
      return;
    }

    switch (eventType) {
      case "meta":
        callbacks.onMeta?.(parsed as { cached: boolean });
        break;
      case "stage":
        callbacks.onStage?.(parsed as { node: string; label: string });
        break;
      case "token":
        callbacks.onToken?.((parsed as { text: string }).text);
        break;
      case "done":
        callbacks.onDone(parsed as RagRiskRecommendationResponse);
        break;
      case "error":
        callbacks.onError((parsed as { message: string }).message);
        break;
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        if (frame.trim()) processFrame(frame);
      }
    }

    if (buffer.trim()) processFrame(buffer);
  } catch (err) {
    if ((err as { name?: string }).name === "AbortError") return;
    callbacks.onError(
      err instanceof Error ? err.message : "스트림 수신 중 오류가 발생했습니다"
    );
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

/* ── 월간 리포트 v2 (format=json, Phase 2 구조화 응답) ── */

export async function fetchMonthlyReportV2(
  month: string /* YYYY-MM */
): Promise<MonthlyReportV2Response | null> {
  try {
    const { data } = await apiClient.get<MonthlyReportV2Response>(
      "/api/v1/health-reports",
      { params: { period: "monthly", month, format: "json" } }
    );
    return data;
  } catch {
    return null;
  }
}

/** 임의 기간 리포트 (period=custom, 캐싱 없음). date_from/date_to 는 YYYY-MM-DD, 양끝 포함. */
export async function fetchMonthlyReportV2Range(
  dateFrom: string /* YYYY-MM-DD */,
  dateTo: string /* YYYY-MM-DD */
): Promise<MonthlyReportV2Response | null> {
  try {
    const { data } = await apiClient.get<MonthlyReportV2Response>(
      "/api/v1/health-reports",
      { params: { period: "custom", date_from: dateFrom, date_to: dateTo, format: "json" } }
    );
    return data;
  } catch {
    return null;
  }
}
