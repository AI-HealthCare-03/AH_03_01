"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type { Challenge } from "@/types/challenge";

/* =========================================
   체크 인증 컴포넌트 (10-C10)
   method=CHECK 인증 — 예/아니오
   ========================================= */

interface CheckVerifyProps {
  challenge: Challenge;
  onSubmit: (checked: boolean, caption?: string) => void;
  loading?: boolean;
}

/* 카테고리별 질문 문구
   ※ NO_SMOKING 은 PHOTO 인증 타입이므로 제외 */
const VERIFY_QUESTIONS: Record<string, string> = {
  NO_ALCOHOL: "오늘 술을 마시지 않으셨나요?",
  SLEEP: "어제 목표 수면 시간을 지키셨나요?",
  MEDITATION: "오늘 명상을 하셨나요?",
  DIET: "오늘 건강한 식사를 하셨나요?",
  DEFAULT: "오늘 챌린지 목표를 달성하셨나요?",
};

export default function CheckVerify({
  challenge,
  onSubmit,
  loading = false,
}: CheckVerifyProps) {
  const [selected, setSelected] = useState<boolean | null>(null);
  const [caption, setCaption] = useState("");

  const config = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;
  const question =
    VERIFY_QUESTIONS[challenge.category] ?? VERIFY_QUESTIONS.DEFAULT;

  const handleSubmit = () => {
    if (selected !== null) {
      onSubmit(selected, caption.trim() || undefined);
    }
  };

  return (
    <div className="flex flex-col items-center text-center">
      {/* 이모지 */}
      <span className="text-6xl mb-4" aria-hidden="true">
        {config.emoji}
      </span>

      {/* 카테고리 라벨 */}
      <p className="text-sm font-semibold text-text-tertiary mb-2">
        {config.label}
      </p>

      {/* 질문 */}
      <h2 className="text-xl font-black text-text-primary mb-8 leading-snug">
        {question}
      </h2>

      {/* 예/아니오 버튼 */}
      <div className="flex gap-4 w-full max-w-xs mb-8">
        <button
          type="button"
          onClick={() => setSelected(false)}
          className={[
            "flex-1 py-5 rounded-[16px] border-2 flex flex-col items-center gap-2 transition-all",
            selected === false
              ? "border-status-danger bg-status-danger-bg"
              : "border-border bg-white hover:border-status-danger",
          ].join(" ")}
          aria-pressed={selected === false}
        >
          <span className="text-3xl" aria-hidden="true">
            ❌
          </span>
          <span className="text-sm font-bold text-text-primary">
            아니요
          </span>
        </button>
        <button
          type="button"
          onClick={() => setSelected(true)}
          className={[
            "flex-1 py-5 rounded-[16px] border-2 flex flex-col items-center gap-2 transition-all",
            selected === true
              ? "border-status-success bg-status-success-bg"
              : "border-border bg-white hover:border-status-success",
          ].join(" ")}
          aria-pressed={selected === true}
        >
          <span className="text-3xl" aria-hidden="true">
            ✅
          </span>
          <span className="text-sm font-bold text-text-primary">
            네, 했어요!
          </span>
        </button>
      </div>

      {/* 한 마디 (caption) */}
      {selected !== null && (
        <div className="w-full max-w-xs mb-6">
          <label
            htmlFor="check-caption"
            className="block text-sm font-semibold text-text-primary mb-2"
          >
            한 마디 <span className="text-text-tertiary font-normal">(선택)</span>
          </label>
          <textarea
            id="check-caption"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            rows={2}
            maxLength={500}
            placeholder="오늘의 소감을 남겨보세요..."
            className="w-full px-4 py-3 rounded-[12px] border border-border text-sm resize-none focus:outline-none focus:border-brand-black"
          />
          <p className="text-xs text-text-tertiary text-right mt-1">
            {caption.length}/500
          </p>
        </div>
      )}

      {/* 확인 버튼 */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        disabled={selected === null}
        loading={loading}
        onClick={handleSubmit}
        className="max-w-xs"
      >
        인증 완료
      </Button>
    </div>
  );
}
