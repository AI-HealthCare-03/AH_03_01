"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import type { ChatDisplayMessage } from "@/types/chat";
import ChatSourceList from "./ChatSource";
import Button from "@/components/ui/Button";

/* =========================================
   챗 메시지 버블
   - USER: 우측 정렬, brand 배경
   - BOT: 좌측 정렬, white 배경
   - fallback: 연한 경고 톤
   - sources + confidence 표시
   - disclaimer 항상 표시 (BOT)
   - CTA: needs_health_data && !has_health_data
   ========================================= */

interface ChatBubbleProps {
  message: ChatDisplayMessage;
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const router = useRouter();
  const isUser = message.role === "USER";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-brand text-brand-black rounded-[16px] rounded-tr-[4px] px-4 py-3 text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  /* BOT 버블 */
  const showCta =
    message.needsHealthData === true && message.hasHealthData === false;

  const bubbleBase = message.isFallback
    ? "bg-[#fff8e1] border border-[#ffe082]"
    : "bg-white border border-border";

  return (
    <div className="flex justify-start">
      <div className={`max-w-[85%] rounded-[16px] rounded-tl-[4px] px-4 py-3 space-y-2 ${bubbleBase}`}>
        {/* fallback 배지 */}
        {message.isFallback && (
          <div className="flex items-center gap-1 text-[11px] text-[#b7791f] font-medium">
            <AlertTriangle size={12} aria-hidden="true" />
            <span>정확한 답변을 드리기 어려울 수 있습니다</span>
          </div>
        )}

        {/* 본문 */}
        <p className="text-sm leading-relaxed text-text-primary whitespace-pre-wrap">
          {message.content}
        </p>

        {/* 출처 (상위 3개 문서명) */}
        <ChatSourceList
          sources={(message.sources ?? []) as import("@/types/chat").ChatSource[]}
        />

        {/* CTA: 건강데이터 입력 유도 */}
        {showCta && (
          <div className="mt-2 p-3 bg-surface rounded-[10px] border border-border space-y-2">
            <p className="text-[12px] text-text-secondary leading-relaxed">
              {message.actionHint ??
                "맞춤 답변을 위해 건강 데이터를 입력해 주세요."}
              {message.missingFields && message.missingFields.length > 0 && (
                <span className="block mt-1 text-text-tertiary">
                  필요 항목: {message.missingFields.join(", ")}
                </span>
              )}
            </p>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => router.push("/health-records/new")}
            >
              건강 데이터 입력하기
            </Button>
          </div>
        )}

        {/* 면책 문구 */}
        {message.disclaimer && (
          <p className="text-[10px] text-text-tertiary border-t border-border pt-2 mt-1">
            {message.disclaimer}
          </p>
        )}
      </div>
    </div>
  );
}
