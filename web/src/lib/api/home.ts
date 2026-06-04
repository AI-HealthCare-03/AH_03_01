/* =========================================
   홈/출석 관련 API 호출 함수
   /api/v1/ prefix 기반 apiClient 사용
   ========================================= */

import apiClient from "./client";
import type {
  Me,
  MyPet,
  ChallengeListResponse,
  PredictionListResponse,
  ChallengeRecommendationResponse,
  AttendanceMonthResponse,
  AttendanceCheckResponse,
  PointBalanceResponse,
  HealthProfileRecord,
  MetricStatResponse,
} from "@/types/api";

/** 내 정보 조회 */
export async function fetchMe(): Promise<Me> {
  const { data } = await apiClient.get<Me>("/api/v1/users/me");
  return data;
}

/** 내 펫 조회 (404 시 null 반환) */
export async function fetchMyPet(): Promise<MyPet | null> {
  try {
    const { data } = await apiClient.get<MyPet>("/api/v1/pets/me");
    return data;
  } catch (err: unknown) {
    const e = err as { response?: { status?: number } };
    if (e?.response?.status === 404) return null;
    throw err;
  }
}

/** 진행 중 챌린지 목록 (ACTIVE + RECRUITING 모두 포함) */
export async function fetchMyActiveChallenges(
  size = 5
): Promise<ChallengeListResponse> {
  const [activeRes, recruitingRes] = await Promise.all([
    apiClient.get<ChallengeListResponse>("/api/v1/challenges", {
      params: { mine: true, status: "ACTIVE", size },
    }),
    apiClient.get<ChallengeListResponse>("/api/v1/challenges", {
      params: { mine: true, status: "RECRUITING", size },
    }),
  ]);
  const items = [
    ...activeRes.data.items,
    ...recruitingRes.data.items,
  ].slice(0, size);
  return {
    items,
    total: activeRes.data.total + recruitingRes.data.total,
    page: 1,
    size,
  };
}

/** 최신 예측 결과 목록 */
export async function fetchLatestPredictions(): Promise<PredictionListResponse> {
  const { data } = await apiClient.get<PredictionListResponse>(
    "/api/v1/predictions",
    { params: { latest: true } }
  );
  return data;
}

/** 예측 ID 기반 추천 챌린지 */
export async function fetchChallengeRecommendations(
  predictionId: number,
  limit = 3
): Promise<ChallengeRecommendationResponse> {
  const { data } = await apiClient.get<ChallengeRecommendationResponse>(
    "/api/v1/challenge-recommendations",
    { params: { predictionId, limit } }
  );
  return data;
}

/** 월간 출석 기록 조회 */
export async function fetchAttendanceMonth(
  month: string /* YYYY-MM */
): Promise<AttendanceMonthResponse> {
  const { data } = await apiClient.get<AttendanceMonthResponse>(
    "/api/v1/attendance-checks",
    { params: { month } }
  );
  return data;
}

/** 오늘 출석 체크 */
export async function postAttendanceCheck(): Promise<AttendanceCheckResponse> {
  const { data } = await apiClient.post<AttendanceCheckResponse>(
    "/api/v1/attendance-checks"
  );
  return data;
}

/** 포인트 잔액 + 최근 거래 내역 */
export async function fetchPointBalance(
  size = 3
): Promise<PointBalanceResponse> {
  const { data } = await apiClient.get<PointBalanceResponse>(
    "/api/v1/points/transactions",
    { params: { size } }
  );
  return data;
}

/** 포인트 거래 내역 (필터링). type/source/기간 지원. */
export async function fetchPointTransactions(filter?: {
  type?: "EARN" | "SPEND";
  source?: string;
  from?: string;
  to?: string;
}): Promise<PointBalanceResponse> {
  const { data } = await apiClient.get<PointBalanceResponse>(
    "/api/v1/points/transactions",
    { params: filter ?? {} }
  );
  return data;
}

/** 건강 프로필 (신장·체중).
 *  백엔드는 recordType=profile 일 때 단일 객체를 반환 (배열 아님). */
export async function fetchHealthProfile(): Promise<HealthProfileRecord | null> {
  try {
    const { data } = await apiClient.get<HealthProfileRecord>(
      "/api/v1/health-records",
      { params: { recordType: "profile" } }
    );
    return data ?? null;
  } catch {
    return null;
  }
}

/** 측정 통계 단일 지표 */
export async function fetchMetricStat(
  metric: string,
  subType?: string
): Promise<MetricStatResponse | null> {
  try {
    const { data } = await apiClient.get<MetricStatResponse>(
      "/api/v1/health-records/statistics",
      { params: { metric, ...(subType ? { subType } : {}), limit: 1 } }
    );
    return data;
  } catch {
    return null;
  }
}
