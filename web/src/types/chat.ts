/* =========================================
   챗봇 도메인 타입 정의
   /api/v1/chat/* 엔드포인트 기반
   ========================================= */

/* ── FAQ ────────────────────────────────── */

export type FaqCategory = "SERVICE" | "DISEASE" | "CHALLENGE" | "ACCOUNT";

export interface FaqResponse {
  id: number;
  category: FaqCategory;
  question: string;
  answer: string;
  sort_order: number;
  short_label: string | null;
}

export interface FaqListResponse {
  faqs: FaqResponse[];
}

/* ── 메시지 송수신 ───────────────────────── */

export type MessageRole = "USER" | "BOT";
export type MessageType = "TEXT" | "FAQ" | "RAG" | "SYSTEM";

export interface ChatSource {
  title?: string;
  url?: string;
  document_id?: number;
  snippet?: string;
  source?: string | null;  /* 문서 코드 (예: "KSH2022") — 문서명 라벨링용 */
}

/** POST /api/v1/chat/messages 요청 바디 */
export interface SendChatMessageRequest {
  message: string;           /* 1~2000자 */
  conversation_id?: number;
  faq_id?: number;
}

/** POST /api/v1/chat/messages 응답 바디 */
export interface ChatMessageResponse {
  conversation_id: number;
  message_id: number;
  role: MessageRole;
  message_type: MessageType;
  answer: string;
  sources: ChatSource[];
  confidence?: number | null;
  model_version?: string | null;
  disclaimer: string;
  intent?: string | null;
  needs_health_data: boolean;
  has_health_data: boolean;
  missing_fields: string[];
  action_hint?: string | null;
  is_fallback: boolean;
  eval_revision_count?: number | null;
}

/* ── 세션 목록 ───────────────────────────── */

export interface ChatSessionListItem {
  id: number;
  title: string | null;
  started_at: string;
  ended_at: string | null;
  last_message_at: string | null;
  message_count: number;
}

export interface ChatSessionListResponse {
  sessions: ChatSessionListItem[];
}

/* ── 세션 상세 (과거 메시지) ──────────────── */

export interface ChatMessageItem {
  id: number;
  role: MessageRole;
  message_type: MessageType;
  content: string;           /* 히스토리 응답의 본문 필드명은 content */
  faq_id: number | null;
  sources: object[];
  confidence: number | null;
  created_at: string;
}

export interface ChatSessionDetailResponse {
  id: number;
  title: string | null;
  started_at: string;
  ended_at: string | null;
  messages: ChatMessageItem[];
}

/* ── 클라이언트 내부 메시지 포맷 ─────────── */

/** 위젯 내부에서 렌더링할 통합 메시지 형식 */
export interface ChatDisplayMessage {
  id: string;                     /* 로컬 UUID (낙관적 업데이트용) */
  role: MessageRole;
  content: string;
  messageType: MessageType;
  sources?: ChatSource[];
  confidence?: number | null;
  disclaimer?: string;
  needsHealthData?: boolean;
  hasHealthData?: boolean;
  missingFields?: string[];
  actionHint?: string | null;
  isFallback?: boolean;
  createdAt: string;
  /* 스트리밍 전용 (SSE 진행 중에만 사용, done 이벤트 후 제거) */
  isStreaming?: boolean;
  stageLabel?: string;
}
