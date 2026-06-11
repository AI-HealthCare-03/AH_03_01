"use client";

import { useEffect, useState } from "react";
import { getAvailableQuizzes, getQuizHistory } from "@/lib/api/community";
import QuizCard from "@/components/community/QuizCard";
import type { QuizResponse, QuizAnswerResponse } from "@/types/community";

const DAILY_LIMIT = 5;
const BASE_DATE = new Date("2026-06-01");

function getDayNumber(quizDate: string): number {
  const diff = Math.round(
    (new Date(quizDate).getTime() - BASE_DATE.getTime()) / (1000 * 60 * 60 * 24)
  );
  return diff + 1;
}

export default function CommunityQuizPage() {
  const [queue, setQueue] = useState<QuizResponse[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answeredOffset, setAnsweredOffset] = useState(0); // 오늘 이미 답변한 문제 수
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalAnswered, setTotalAnswered] = useState(0);
  const [totalPoints, setTotalPoints] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const todayStr = new Date().toISOString().slice(0, 10);

    Promise.all([getAvailableQuizzes(), getQuizHistory({ size: DAILY_LIMIT })])
      .then(([quizzes, history]) => {
        // 오늘 답변한 항목만 필터링
        const todayHistory = history.filter((a) => a.attempted_at.slice(0, 10) === todayStr);
        const offset = todayHistory.length;
        const points = todayHistory.reduce((sum, a) => sum + a.points_earned, 0);

        setAnsweredOffset(offset);
        setTotalAnswered(offset);
        setTotalPoints(points);

        if (quizzes.length === 0) setDone(true);
        else setQueue(quizzes);
      })
      .catch(() => setError("퀴즈를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  function handleAnswered(result: QuizAnswerResponse) {
    setTotalAnswered((n) => n + 1);
    setTotalPoints((p) => p + result.points_earned);
  }

  function handleNext() {
    if (currentIndex + 1 >= queue.length) {
      setDone(true);
    } else {
      setCurrentIndex((i) => i + 1);
    }
  }

  const current = queue[currentIndex];
  // 오늘 전체 기준 번호 (이미 푼 문제 수 + 현재 인덱스 + 1)
  const displayNumber = answeredOffset + currentIndex + 1;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-black text-text-primary">건강 퀴즈</h1>

      <div className="max-w-xl">
        {loading && (
          <p className="py-16 text-center text-text-secondary text-sm">퀴즈 불러오는 중...</p>
        )}

        {error && (
          <p className="py-16 text-center text-text-secondary text-sm">{error}</p>
        )}

        {done && (
          <div className="rounded-3xl bg-brand p-8 flex flex-col items-center gap-3 text-center">
            <p className="text-4xl">🎉</p>
            <p className="text-xl font-black text-gray-900">오늘 퀴즈 완료!</p>
            <p className="text-sm text-gray-700">
              총 {totalAnswered}문제 · +{totalPoints}P 획득
            </p>
            <p className="text-xs text-gray-500 mt-1">내일 새로운 퀴즈가 기다리고 있어요.</p>
          </div>
        )}

        {!loading && !error && !done && current && (
          <>
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="text-xs text-text-secondary">
                {displayNumber} / {DAILY_LIMIT}문제
              </span>
              {totalPoints > 0 && (
                <span className="text-xs font-semibold text-amber-600">+{totalPoints}P 획득</span>
              )}
            </div>
            <QuizCard
              key={current.id}
              quiz={current}
              dayNumber={getDayNumber(current.quiz_date)}
              hasNext={currentIndex + 1 < queue.length}
              onAnswered={handleAnswered}
              onNext={handleNext}
            />
          </>
        )}
      </div>
    </div>
  );
}
