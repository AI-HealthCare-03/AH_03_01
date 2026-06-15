"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { getTodayQuiz } from "@/lib/api/community";
import type { QuizCategory } from "@/types/community";

const CATEGORY_LABEL: Record<QuizCategory, string> = {
  BLOOD_SUGAR: "당뇨",
  BLOOD_PRESSURE: "고혈압",
  DIET: "식단",
  EXERCISE: "운동",
  GENERAL: "건강",
};

export default function HealthQuizCard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["quiz", "today"],
    queryFn: getTodayQuiz,
    staleTime: 1000 * 60 * 5,
    retry: false,
  });

  const is404 = isError && axios.isAxiosError(error) && error.response?.status === 404;
  const completed = data?.already_answered ?? false;
  const quiz = data?.quiz;

  return (
    <article
      aria-label="오늘의 건강 퀴즈"
      className="bg-white rounded-[16px] border border-border p-5 flex flex-col gap-4 shadow-sm relative"
    >
      {/* 헤더 */}
      <div className="flex items-center gap-2">
        <span className="text-xl" aria-hidden="true">🧠</span>
        <h2 className="text-base font-bold text-text-primary">
          오늘의 건강 퀴즈
        </h2>
      </div>

      {isLoading ? (
        <p className="text-sm text-text-tertiary">불러오는 중…</p>
      ) : isError && !is404 ? (
        <p className="text-sm text-text-tertiary">퀴즈를 불러오지 못했어요.</p>
      ) : completed || is404 ? (
        <div className="flex flex-col items-center justify-center gap-2 pt-8 pb-2">
          <p className="text-base font-bold text-green-600">오늘 퀴즈 완료! 🎉</p>
          <p className="text-sm text-text-tertiary text-center">내일 새로운 퀴즈가 기다리고 있어요.</p>
        </div>
      ) : quiz ? (
        <>
          {/* 카테고리 라벨 */}
          <p className="text-xs font-semibold text-text-tertiary">
            {CATEGORY_LABEL[quiz.category] ?? quiz.category}
          </p>

          {/* 질문 */}
          <p className="text-sm font-semibold text-text-primary leading-snug">
            {quiz.question}
          </p>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 pt-8 pb-2">
          <p className="text-base font-bold text-green-600">오늘 퀴즈 완료! 🎉</p>
          <p className="text-sm text-text-tertiary text-center">내일 새로운 퀴즈가 기다리고 있어요.</p>
        </div>
      )}

      {/* 하단 링크 */}
      <div className="mt-auto pt-2 border-t border-border">
        <Link
          href="/community/quiz"
          className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
        >
          {completed ? "퀴즈 기록 보기 →" : "퀴즈 풀러가기 →"}
        </Link>
      </div>
    </article>
  );
}
