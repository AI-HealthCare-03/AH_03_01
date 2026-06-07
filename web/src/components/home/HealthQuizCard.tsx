"use client";

/* =========================================
   오늘의 건강 퀴즈 카드 (C 카드)
   백엔드 미구현 → 완전 정적 mock 데이터
   ========================================= */

import Link from "next/link";

/* mock 데이터 — 백엔드 구현 전까지 정적 */
const MOCK_QUIZ = {
  day: 14,
  category: "당뇨",
  question: "한국인 공복혈당의 정상 범위는?",
  correctRate: 83,
  reward: 50,
};

export default function HealthQuizCard() {
  return (
    <article
      aria-label="오늘의 건강 퀴즈"
      className="bg-white rounded-[16px] border border-border p-5 flex flex-col gap-4 shadow-sm relative"
    >
      {/* 베타 표시 */}
      <span
        className="absolute top-3 right-3 text-[10px] text-text-disabled"
        aria-label="베타 서비스, 곧 출시 예정"
      >
        베타 · 곧 출시
      </span>

      {/* 헤더 */}
      <div className="flex items-center gap-2">
        <span className="text-xl" aria-hidden="true">🧠</span>
        <h2 className="text-base font-bold text-text-primary">
          오늘의 건강 퀴즈
        </h2>
      </div>

      {/* DAY + 카테고리 라벨 */}
      <p className="text-xs font-semibold text-text-tertiary">
        DAY {MOCK_QUIZ.day} · {MOCK_QUIZ.category}
      </p>

      {/* 질문 */}
      <p className="text-sm font-semibold text-text-primary leading-snug">
        {MOCK_QUIZ.question}
      </p>

      {/* 통계 */}
      <div className="flex items-center gap-4">
        <div className="flex flex-col">
          <span className="text-[10px] text-text-tertiary">정답률</span>
          <span className="text-base font-bold text-text-primary">
            {MOCK_QUIZ.correctRate}%
          </span>
        </div>
        <div className="w-px h-8 bg-border" aria-hidden="true" />
        <div className="flex flex-col">
          <span className="text-[10px] text-text-tertiary">보상</span>
          <span className="text-base font-bold text-brand-black">
            +{MOCK_QUIZ.reward}P
          </span>
        </div>
      </div>

      {/* 하단 링크 */}
      <div className="mt-auto pt-2 border-t border-border">
        <Link
          href="/community/quiz"
          className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
        >
          퀴즈 풀러가기 →
        </Link>
      </div>
    </article>
  );
}
