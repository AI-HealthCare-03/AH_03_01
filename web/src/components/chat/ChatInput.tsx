"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

/* =========================================
   메시지 입력창 + 전송 버튼
   - Enter 전송 / Shift+Enter 줄바꿈
   - 1~2000자 제한
   - 전송 중 비활성화
   ========================================= */

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length >= 1 && !disabled;

  const handleSend = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
    /* 전송 후 textarea 높이 초기화 */
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  return (
    <div className="border-t border-border bg-white px-3 py-3">
      <div className="flex items-end gap-2 bg-surface rounded-[14px] border border-border px-3 py-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          maxLength={2000}
          rows={1}
          placeholder="건강에 대해 물어보세요..."
          aria-label="메시지 입력"
          className={[
            "flex-1 resize-none bg-transparent text-sm text-text-primary",
            "placeholder:text-text-tertiary outline-none leading-relaxed",
            "min-h-[24px] max-h-[120px]",
            disabled ? "cursor-not-allowed opacity-50" : "",
          ].join(" ")}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={!canSend}
          aria-label="전송"
          className={[
            "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all",
            canSend
              ? "bg-brand-black text-white hover:opacity-80 active:scale-90"
              : "bg-surface text-text-tertiary cursor-not-allowed",
          ].join(" ")}
        >
          <Send size={15} aria-hidden="true" />
        </button>
      </div>
      {value.length > 1800 && (
        <p className="text-[10px] text-text-tertiary text-right mt-1 px-1">
          {value.length}/2000
        </p>
      )}
    </div>
  );
}
