"use client";

/* =========================================
   타이핑 인디케이터 (BOT 응답 대기 중)
   ========================================= */

export default function TypingIndicator() {
  return (
    <div className="flex justify-start" aria-live="polite" aria-label="답변 생성 중">
      <div className="bg-white border border-border rounded-[16px] rounded-tl-[4px] px-4 py-3 flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
            aria-hidden="true"
          />
        ))}
      </div>
    </div>
  );
}
