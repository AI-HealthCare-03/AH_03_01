"use client";

import { useEffect } from "react";
import { X, RotateCcw, History } from "lucide-react";
import { useChatStore } from "@/stores/chat";
import { useSendChatMessage } from "@/hooks/queries/useSendChatMessage";
import { useChatSession } from "@/hooks/queries/useChatSession";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { FaqResponse, ChatDisplayMessage } from "@/types/chat";
import ChatMessageList from "./ChatMessageList";
import ChatInput from "./ChatInput";
import ChatSessionList, {
  sessionMessageToDisplay,
} from "./ChatSessionList";

/* =========================================
   챗 위젯 패널 (헤더 + 본문 + 푸터)
   - 헤더: 타이틀 / 세션목록 토글 / 새 대화 / 닫기
   - 본문: 메시지 목록 | 세션 목록 뷰 전환
   - 푸터: ChatInput
   ========================================= */

export default function ChatPanel() {
  const {
    view,
    setView,
    conversationId,
    messages,
    addMessage,
    setMessages,
    setConversationId,
    startNewConversation,
    closeChat,
  } = useChatStore();

  const { showToast } = useToast();
  const sendMutation = useSendChatMessage();

  /* 세션 선택 후 상세 로드 */
  const { data: sessionDetail } = useChatSession(
    view === "chat" && conversationId != null ? conversationId : undefined
  );

  /* 세션 상세가 로드되면 메시지 목록을 히스토리로 교체 */
  useEffect(() => {
    if (!sessionDetail) return;
    /* 이미 동일 세션의 메시지가 로드되어 있으면 스킵 */
    if (
      messages.length > 0 &&
      messages[0].id === String(sessionDetail.messages[0]?.id)
    )
      return;
    setMessages(sessionDetail.messages.map(sessionMessageToDisplay));
  }, [sessionDetail]); // eslint-disable-line react-hooks/exhaustive-deps

  /* 메시지 전송 처리 */
  const handleSend = (text: string) => {
    /* 낙관적 사용자 메시지 추가 */
    const optimisticUserMsg: ChatDisplayMessage = {
      id: crypto.randomUUID(),
      role: "USER",
      content: text,
      messageType: "TEXT",
      createdAt: new Date().toISOString(),
    };
    addMessage(optimisticUserMsg);

    sendMutation.mutate(
      {
        body: {
          message: text,
          conversation_id: conversationId ?? undefined,
        },
        mode: "rag",
      },
      {
        onSuccess: (data) => {
          /* conversation_id 첫 응답에서 세팅 */
          if (!conversationId) {
            setConversationId(data.conversation_id);
          }
          const botMsg: ChatDisplayMessage = {
            id: crypto.randomUUID(),
            role: "BOT",
            content: data.answer,
            messageType: data.message_type,
            sources: data.sources ?? [],
            confidence: data.confidence,
            disclaimer: data.disclaimer,
            needsHealthData: data.needs_health_data,
            hasHealthData: data.has_health_data,
            missingFields: data.missing_fields,
            actionHint: data.action_hint,
            isFallback: data.is_fallback,
            createdAt: new Date().toISOString(),
          };
          addMessage(botMsg);
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  /* FAQ 칩 클릭 처리 */
  const handleFaqSelect = (faq: FaqResponse) => {
    const optimisticUserMsg: ChatDisplayMessage = {
      id: crypto.randomUUID(),
      role: "USER",
      content: faq.question,
      messageType: "FAQ",
      createdAt: new Date().toISOString(),
    };
    addMessage(optimisticUserMsg);

    sendMutation.mutate(
      {
        body: {
          message: faq.question,
          conversation_id: conversationId ?? undefined,
          faq_id: faq.id,
        },
        mode: "faq",
      },
      {
        onSuccess: (data) => {
          if (!conversationId) {
            setConversationId(data.conversation_id);
          }
          const botMsg: ChatDisplayMessage = {
            id: crypto.randomUUID(),
            role: "BOT",
            content: data.answer,
            messageType: data.message_type,
            sources: data.sources ?? [],
            confidence: data.confidence,
            disclaimer: data.disclaimer,
            needsHealthData: data.needs_health_data,
            hasHealthData: data.has_health_data,
            missingFields: data.missing_fields,
            actionHint: data.action_hint,
            isFallback: data.is_fallback,
            createdAt: new Date().toISOString(),
          };
          addMessage(botMsg);
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  /* 세션 목록에서 세션 선택 */
  const handleSessionSelect = (sessionId: number) => {
    setConversationId(sessionId);
    setMessages([]); /* 로드 전 빈 상태로 초기화 → useEffect 가 채움 */
    setView("chat");
  };

  return (
    <div
      className={[
        "flex flex-col bg-[#f8f8f8]",
        /* 모바일: 전체화면에 가깝게 / 데스크탑: 고정 크기 */
        "w-full h-full md:w-[380px] md:h-[600px]",
        "rounded-t-[20px] md:rounded-[20px]",
        "overflow-hidden shadow-2xl",
      ].join(" ")}
      role="dialog"
      aria-label="건강 도우미 챗봇"
      aria-modal="true"
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-brand-black">
            건강 도우미
          </span>
          {conversationId && (
            <span className="text-[10px] text-text-tertiary bg-surface px-2 py-0.5 rounded-full">
              대화 중
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* 세션 목록 토글 */}
          <button
            type="button"
            onClick={() =>
              setView(view === "sessions" ? "chat" : "sessions")
            }
            aria-label={view === "sessions" ? "대화로 돌아가기" : "대화 기록 보기"}
            aria-pressed={view === "sessions"}
            className="p-2 rounded-[8px] text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
          >
            <History size={16} aria-hidden="true" />
          </button>
          {/* 새 대화 */}
          <button
            type="button"
            onClick={startNewConversation}
            aria-label="새 대화 시작"
            className="p-2 rounded-[8px] text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
          >
            <RotateCcw size={16} aria-hidden="true" />
          </button>
          {/* 닫기 */}
          <button
            type="button"
            onClick={closeChat}
            aria-label="챗봇 닫기"
            className="p-2 rounded-[8px] text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* 본문 */}
      {view === "sessions" ? (
        <ChatSessionList onSessionSelect={handleSessionSelect} />
      ) : (
        <ChatMessageList
          messages={messages}
          isLoading={sendMutation.isPending}
          onFaqSelect={handleFaqSelect}
        />
      )}

      {/* 입력창 (chat 뷰에서만) */}
      {view === "chat" && (
        <ChatInput
          onSend={handleSend}
          disabled={sendMutation.isPending}
        />
      )}
    </div>
  );
}
