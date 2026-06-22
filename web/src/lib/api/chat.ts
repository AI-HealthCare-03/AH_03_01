/* =========================================
   챗봇 도메인 API 호출 함수
   /api/v1/chat/* 엔드포인트 기반 apiClient 사용
   ========================================= */

import apiClient from "./client";
import { API_BASE_URL, ROUTES } from "@/constants";
import { getToken, removeToken } from "@/lib/tokens";
import type {
  FaqListResponse,
  FaqResponse,
  SendChatMessageRequest,
  ChatMessageResponse,
  ChatSessionListResponse,
  ChatSessionListItem,
  ChatSessionDetailResponse,
} from "@/types/chat";

/* ── SSE 스트리밍 메시지 전송 ─────────────── */

export interface StreamChatCallbacks {
  onMeta: (conversationId: number) => void;
  onStage: (payload: { node: string; label: string }) => void;
  onToken: (text: string) => void;
  onDone: (payload: ChatMessageResponse) => void;
  onError: (message: string) => void;
}

export async function streamChatMessage(
  body: SendChatMessageRequest,
  callbacks: StreamChatCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const url = `${API_BASE_URL}/api/v1/chat/messages/stream?mode=rag`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
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
      case "meta": {
        const p = parsed as { conversation_id: number };
        callbacks.onMeta(p.conversation_id);
        break;
      }
      case "stage": {
        const p = parsed as { node: string; label: string };
        callbacks.onStage(p);
        break;
      }
      case "token": {
        const p = parsed as { text: string };
        callbacks.onToken(p.text);
        break;
      }
      case "done": {
        callbacks.onDone(parsed as ChatMessageResponse);
        break;
      }
      case "error": {
        const p = parsed as { message: string };
        callbacks.onError(p.message);
        break;
      }
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
