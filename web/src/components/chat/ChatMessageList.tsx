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
      {/* 인사 버블 — 항상 최상단 고정 */}
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-white border border-border rounded-[16px] rounded-tl-[4px] px-4 py-3 space-y-1">
          <p className="text-sm font-semibold text-text-primary">
            안녕하세요! 케어로그 건강 도우미예요 👋
          </p>
          <p className="text-sm leading-relaxed text-text-secondary">
            만성질환 관리, 생활습관, 챌린지에 대해 무엇이든 물어보세요!
          </p>
        </div>
      </div>

      {isEmpty ? (
        <FaqChips onSelect={onFaqSelect} />
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
