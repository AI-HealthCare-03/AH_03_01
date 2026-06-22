"use client";

import { useMemo } from "react";
import { useFaqs } from "@/hooks/queries/useFaqs";
import type { FaqResponse } from "@/types/chat";

interface FaqChipsProps {
  onSelect: (faq: FaqResponse) => void;
}

function chipLabel(faq: { question: string; short_label: string | null }) {
  return faq.short_label ?? faq.question;
}

export default function FaqChips({ onSelect }: FaqChipsProps) {
  const { data: faqs, isLoading } = useFaqs();

  const picked = useMemo(() => {
    if (!faqs || faqs.length === 0) return [];
    const shuffled = [...faqs].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 5);
  }, [faqs]);

  if (isLoading) {
    return (
      <div className="space-y-2 px-4">
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 w-24 bg-surface rounded-full animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (picked.length === 0) return null;

  return (
    <div className="space-y-2 px-4">
      <p className="text-xs text-text-tertiary font-medium">자주 묻는 질문</p>
      <div className="flex flex-wrap gap-2">
        {picked.map((faq) => (
          <button
            key={faq.id}
            type="button"
            onClick={() => onSelect(faq)}
            title={faq.question}
            className={[
              "text-[12px] px-3 py-1.5 rounded-full border transition-colors",
              "border-border bg-white text-text-secondary",
              "hover:border-brand-black hover:text-brand-black hover:bg-surface",
              "active:scale-95",
            ].join(" ")}
          >
            {chipLabel(faq)}
          </button>
        ))}
      </div>
    </div>
  );
}
