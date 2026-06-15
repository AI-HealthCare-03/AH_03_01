"use client";

import { useEffect, useRef, useState } from "react";
import { X, RotateCcw, History } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "@/stores/chat";
import { useSendChatMessage } from "@/hooks/queries/useSendChatMessage";
import { useChatSession } from "@/hooks/queries/useChatSession";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { streamChatMessage } from "@/lib/api/chat";
import { CHAT_SESSIONS_KEY } from "@/hooks/queries/useChatSessions";
import { CHAT_SESSION_KEY } from "@/hooks/queries/useChatSession";
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
    updateMessage,
    removeMessage,
    startNewConversation,
    closeChat,
  } = useChatStore();

  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const sendMutation = useSendChatMessage();

  /* SSE 스트리밍 진행 중 여부 */
  const [isStreaming, setIsStreaming] = useState(false);
  /* AbortController ref — 컴포넌트 언마운트 or 새 대화 시작 시 스트림 중단 */
  const abortRef = useRef<AbortController | null>(null);

  /* 세션 선택 후 상세 로드 */
  const { data: sessionDetail } = useChatSession(
    view === "chat" && conversationId != null ? conversationId : undefined
  );

  /* 세션 상세가 로드되면 메시지 목록을 히스토리로 교체.
     단, 로컬에서 구동 중인(낙관적/스트리밍) 메시지가 있으면 서버 히스토리로 덮지 않는다.
     스트리밍 중 onMeta 가 conversationId 를 세팅하면 useChatSession 이 활성화되어
     세션 상세를 fetch 하는데, 그때 라이브 메시지를 클로버하면 스트리밍 UI 가 사라진다.
     세션 목록에서 명시적으로 세션을 선택하면 handleSessionSelect 가 setMessages([]) 로
     비우므로, 그 빈 상태일 때만 히스토리로 하이드레이트한다. */
  useEffect(() => {
    if (!sessionDetail) return;
    if (messages.length > 0) return;
    setMessages(sessionDetail.messages.map(sessionMessageToDisplay));
  }, [sessionDetail]); // eslint-disable-line react-hooks/exhaustive-deps

  /* 언마운트 시 진행 중 스트림 중단 */
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  /* SSE 스트리밍 메시지 전송 처리 (RAG 모드) */
  const handleSend = (text: string) => {
    /* 이전 스트림이 진행 중이면 중단 */
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    /* 낙관적 사용자 메시지 추가 */
    const optimisticUserMsg: ChatDisplayMessage = {
      id: crypto.randomUUID(),
      role: "USER",
      content: text,
      messageType: "TEXT",
      createdAt: new Date().toISOString(),
    };
    addMessage(optimisticUserMsg);

    /* 진행 중 BOT placeholder 즉시 추가 */
    const botId = crypto.randomUUID();
    const placeholderBotMsg: ChatDisplayMessage = {
      id: botId,
      role: "BOT",
      content: "",
      messageType: "RAG",
      isStreaming: true,
      stageLabel: "질문을 준비하고 있어요...",
      createdAt: new Date().toISOString(),
    };
    addMessage(placeholderBotMsg);
    setIsStreaming(true);

    /* token 청크를 누적할 로컬 변수 (클로저 캡처용) */
    let accumulatedContent = "";

    streamChatMessage(
      {
        message: text,
        conversation_id: conversationId ?? undefined,
      },
      {
        onMeta: (cid) => {
          if (!conversationId) setConversationId(cid);
        },
        onStage: ({ label }) => {
          updateMessage(botId, { stageLabel: label });
        },
        onToken: (tokenText) => {
          accumulatedContent += tokenText;
          updateMessage(botId, { content: accumulatedContent, stageLabel: undefined });
        },
        onDone: (payload) => {
          updateMessage(botId, {
            content: payload.answer,
            messageType: payload.message_type,
            sources: payload.sources ?? [],
            confidence: payload.confidence,
            disclaimer: payload.disclaimer,
            needsHealthData: payload.needs_health_data,
            hasHealthData: payload.has_health_data,
            missingFields: payload.missing_fields,
            actionHint: payload.action_hint,
            isFallback: payload.is_fallback,
            isStreaming: false,
            stageLabel: undefined,
          });
          setIsStreaming(false);
          /* 세션 목록·상세 갱신 (useSendChatMessage onSuccess 와 동일 효과) */
          queryClient.invalidateQueries({ queryKey: [CHAT_SESSIONS_KEY] });
          queryClient.invalidateQueries({ queryKey: [CHAT_SESSION_KEY, payload.conversation_id] });
        },
        onError: (message) => {
          removeMessage(botId);
          setIsStreaming(false);
          showToast(message, "error");
        },
      },
      controller.signal
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
        "w-full h-full md:w-[380px] md:h-[600px] md:max-h-full",
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
          isLoading={sendMutation.isPending || isStreaming}
          onFaqSelect={handleFaqSelect}
        />
      )}

      {/* 입력창 (chat 뷰에서만) */}
      {view === "chat" && (
        <ChatInput
          onSend={handleSend}
          disabled={sendMutation.isPending || isStreaming}
        />
      )}
    </div>
  );
}
