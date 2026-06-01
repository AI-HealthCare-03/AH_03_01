"use client";

import { useFaqs } from "@/hooks/queries/useFaqs";
import type { FaqResponse } from "@/types/chat";

/* =========================================
   FAQ 칩 목록
   - 대화 없을 때 / 새 대화 시작 시 표시
   - 클릭 → onSelect(faq) 콜백
   ========================================= */

interface FaqChipsProps {
  onSelect: (faq: FaqResponse) => void;
}

export default function FaqChips({ onSelect }: FaqChipsProps) {
  const { data: faqs, isLoading } = useFaqs();

  if (isLoading) {
    return (
      <div className="space-y-2 px-4">
        <p className="text-xs text-text-tertiary">자주 묻는 질문을 불러오는 중...</p>
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-8 w-28 bg-surface rounded-full animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!faqs || faqs.length === 0) return null;

  return (
    <div className="space-y-2 px-4">
      <p className="text-xs text-text-tertiary font-medium">자주 묻는 질문</p>
      <div className="flex flex-wrap gap-2">
        {faqs.slice(0, 8).map((faq) => (
          <button
            key={faq.id}
            type="button"
            onClick={() => onSelect(faq)}
            className={[
              "text-[12px] px-3 py-1.5 rounded-full border transition-colors",
              "border-border bg-white text-text-secondary",
              "hover:border-brand-black hover:text-brand-black hover:bg-surface",
              "active:scale-95",
            ].join(" ")}
          >
            {faq.question}
          </button>
        ))}
      </div>
    </div>
  );
}
