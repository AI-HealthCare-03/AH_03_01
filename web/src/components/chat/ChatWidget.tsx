"use client";

import Image from "next/image";
import { X } from "lucide-react";
import { useChatStore } from "@/stores/chat";
import ChatPanel from "./ChatPanel";

/* =========================================
   플로팅 챗 위젯
   - 토글 버튼 (우하단 고정)
   - 열리면 패널 오버레이
   - 모바일: 하단 탭바(56px) 위에 위치
   - 데스크탑: 우하단 20px 고정
   ========================================= */

export default function ChatWidget() {
  const { isOpen, toggleChat } = useChatStore();

  return (
    <>
      {/* 패널 (열림 상태) */}
      {isOpen && (
        <div
          className={[
            "fixed z-50",
            /* 모바일: 하단 탭바(56px) + 버튼 여백(80px) 위, 전체 너비, 최대 높이 지정 */
            "bottom-[136px] left-0 right-0 mx-2 h-[60vh]",
            /* 데스크탑: 우하단 고정, 뷰포트 높이 제한으로 작은 창에서도 스크롤 동작 */
            "md:bottom-[88px] md:left-auto md:right-5 md:mx-0 md:h-[600px] md:max-h-[calc(100vh-120px)]",
          ].join(" ")}
        >
          <ChatPanel />
        </div>
      )}

      {/* 토글 버튼 */}
      <button
        type="button"
        onClick={toggleChat}
        aria-label={isOpen ? "챗봇 닫기" : "건강 도우미 열기"}
        aria-expanded={isOpen}
        className={[
          "fixed z-50",
          /* 모바일: 탭바(56px) 바로 위 + 여유 */
          "bottom-[68px] right-4",
          /* 데스크탑 */
          "md:bottom-5 md:right-5",
          /* 버튼 스타일 */
          "w-14 h-14 rounded-full shadow-lg flex items-center justify-center overflow-hidden",
          "transition-all duration-200 active:scale-90",
          /* 닫힘: 마스코트 이미지가 원형 배경을 채움 / 열림: 검은 원 + X */
          isOpen ? "bg-brand-black text-white" : "bg-transparent",
        ].join(" ")}
      >
        {isOpen ? (
          <X size={24} aria-hidden="true" />
        ) : (
          <Image
            src="/chat-button.png"
            alt=""
            width={56}
            height={56}
            priority
            className="w-14 h-14 object-cover"
          />
        )}
      </button>
    </>
  );
}
