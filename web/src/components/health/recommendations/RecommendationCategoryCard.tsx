"use client";

import { useState } from "react";

interface RecommendationCategoryCardProps {
  icon: string;
  title: string;
  content: string;
  /** 데스크탑에서 "자세히" 버튼 클릭 시 실행될 콜백 (선택) */
  onDetailClick?: () => void;
  isDetailAvailable?: boolean;
}

export default function RecommendationCategoryCard({
  icon,
  title,
  content,
  onDetailClick,
  isDetailAvailable,
}: RecommendationCategoryCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-white rounded-[16px] shadow-[0_1px_4px_rgba(0,0,0,0.08)] overflow-hidden">
      {/* 아코디언 헤더 */}
      <button
        type="button"
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl" aria-hidden="true">{icon}</span>
          <span className="font-bold text-text-primary">{title}</span>
        </div>
        <span
          className={[
            "text-text-tertiary transition-transform duration-200",
            open ? "rotate-180" : "",
          ].join(" ")}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>

      {/* 아코디언 본문 */}
      {open && (
        <div className="px-5 pb-5 border-t border-border">
          <p className="text-sm text-text-secondary mt-3 leading-relaxed whitespace-pre-line">
            {content}
          </p>
          {isDetailAvailable && onDetailClick && (
            <button
              type="button"
              onClick={onDetailClick}
              className="mt-3 hidden md:inline-flex items-center gap-1 text-sm font-semibold text-text-primary underline hover:opacity-70 transition-opacity"
            >
              {title} 자세히 보기 →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
