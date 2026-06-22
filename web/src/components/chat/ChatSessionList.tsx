"use client";

import { useChatSessions } from "@/hooks/queries/useChatSessions";
import { useChatStore } from "@/stores/chat";
import type { ChatDisplayMessage, ChatMessageItem } from "@/types/chat";
import { MessageCircle } from "lucide-react";

/* =========================================
   세션 목록 뷰
   - 과거 대화 목록 표시
   - 클릭 시 해당 세션의 메시지를 로드하여 이어쓰기
   ========================================= */

interface ChatSessionListProps {
  onSessionSelect: (sessionId: number) => void;
}

export default function ChatSessionList({
  onSessionSelect,
}: ChatSessionListProps) {
  const { data: sessions, isLoading, isError } = useChatSessions();

  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-surface rounded-[12px] animate-pulse" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex-1 flex items-center justify-center px-4">
        <p className="text-sm text-text-secondary text-center">
          대화 목록을 불러오지 못했습니다.
          <br />
          잠시 후 다시 시도해 주세요.
        </p>
      </div>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 px-4 text-center">
        <MessageCircle size={40} className="text-text-tertiary" aria-hidden="true" />
        <p className="text-sm text-text-secondary">아직 대화 기록이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
      {sessions.map((session) => {
        const displayTitle = session.title ?? "새 대화";
        const lastAt = session.last_message_at ?? session.started_at;
        const dateLabel = formatRelativeDate(lastAt);

        return (
          <button
            key={session.id}
            type="button"
            onClick={() => onSessionSelect(session.id)}
            className={[
              "w-full text-left px-4 py-3 rounded-[12px] border border-border bg-white",
              "hover:bg-surface hover:border-brand-black transition-colors",
              "flex flex-col gap-1",
            ].join(" ")}
          >
            <span className="text-sm font-medium text-text-primary line-clamp-1">
              {displayTitle}
            </span>
            <span className="text-[11px] text-text-tertiary">
              {dateLabel} · {session.message_count}개 메시지
            </span>
          </button>
        );
      })}
    </div>
  );
}

function formatRelativeDate(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "방금";
    if (diffMin < 60) return `${diffMin}분 전`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}시간 전`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}일 전`;
    return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

/* ── 세션 선택 시 메시지 로드 훅 (패널에서 사용) ── */

export function useLoadSessionMessages() {
  const { setConversationId, setView } = useChatStore();

  const loadSession = (sessionId: number) => {
    /* 세션 ID 바로 세팅 → useChatSession 훅이 enabled 됨 */
    setConversationId(sessionId);
    setView("chat");
  };

  return { loadSession };
}

/** 세션 상세를 ChatDisplayMessage[] 로 변환 */
export function sessionMessageToDisplay(
  item: ChatMessageItem
): ChatDisplayMessage {
  return {
    id: String(item.id),
    role: item.role,
    content: item.content,
    messageType: item.message_type,
    sources: (item.sources ?? []) as import("@/types/chat").ChatSource[],
    confidence: item.confidence,
    createdAt: item.created_at,
  };
}
