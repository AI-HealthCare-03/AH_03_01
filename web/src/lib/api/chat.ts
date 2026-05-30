/* =========================================
   챗봇 도메인 API 호출 함수
   /api/v1/chat/* 엔드포인트 기반 apiClient 사용
   ========================================= */

import apiClient from "./client";
import type {
  FaqListResponse,
  FaqResponse,
  SendChatMessageRequest,
  ChatMessageResponse,
  ChatSessionListResponse,
  ChatSessionListItem,
  ChatSessionDetailResponse,
} from "@/types/chat";

/* ── FAQ 목록 ─────────────────────────────── */

export async function fetchFaqs(params?: {
  category?: string;
  keyword?: string;
}): Promise<FaqResponse[]> {
  try {
    const { data } = await apiClient.get<FaqListResponse>("/api/v1/chat/faqs", {
      params,
    });
    return data?.faqs ?? [];
  } catch {
    return [];
  }
}

/* ── 메시지 전송 ──────────────────────────── */

export async function sendChatMessage(
  body: SendChatMessageRequest,
  mode: "rag" | "faq" = "rag"
): Promise<ChatMessageResponse> {
  const { data } = await apiClient.post<ChatMessageResponse>(
    "/api/v1/chat/messages",
    body,
    { params: { mode } }
  );
  return data;
}

/* ── 세션 목록 ────────────────────────────── */

export async function fetchChatSessions(): Promise<ChatSessionListItem[]> {
  try {
    const { data } = await apiClient.get<ChatSessionListResponse>(
      "/api/v1/chat/sessions"
    );
    return data?.sessions ?? [];
  } catch {
    return [];
  }
}

/* ── 세션 상세 (과거 메시지) ─────────────── */

export async function fetchChatSession(
  sessionId: number
): Promise<ChatSessionDetailResponse | null> {
  try {
    const { data } = await apiClient.get<ChatSessionDetailResponse>(
      `/api/v1/chat/sessions/${sessionId}`
    );
    return data ?? null;
  } catch {
    return null;
  }
}
