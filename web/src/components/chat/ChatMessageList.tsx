"use client";

import { useEffect, useRef } from "react";
import type { ChatDisplayMessage } from "@/types/chat";
import ChatBubble from "./ChatBubble";
import TypingIndicator from "./TypingIndicator";
import type { FaqResponse } from "@/types/chat";
import FaqChips from "./FaqChips";

/* =========================================
   메시지 목록 스크롤 영역
   ========================================= */

interface ChatMessageListProps {
  messages: ChatDisplayMessage[];
  isLoading: boolean;
  onFaqSelect: (faq: FaqResponse) => void;
}

export default function ChatMessageList({
  messages,
  isLoading,
  onFaqSelect,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  /* 새 메시지 올 때마다 자동 스크롤 */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const isEmpty = messages.length === 0;

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
      aria-label="대화 내용"
    >
      {isEmpty ? (
        /* 빈 상태: 안내 + FAQ 칩 */
        <div className="space-y-4">
          <div className="text-center py-4">
            <p className="text-sm font-semibold text-text-primary">
              헬씨루틴 건강 도우미
            </p>
            <p className="text-xs text-text-secondary mt-1 leading-relaxed">
              만성질환 관리, 챌린지, 생활습관에 대해<br />
              무엇이든 물어보세요.
            </p>
          </div>
          <FaqChips onSelect={onFaqSelect} />
        </div>
      ) : (
        <>
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {/* 스트리밍 placeholder 가 없는 경우에만 TypingIndicator 표시 (FAQ 모드 폴백) */}
          {isLoading && !messages.some((m) => m.isStreaming) && <TypingIndicator />}
        </>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
