"use client";

import { useEffect, useState } from "react";
import { getAvailableQuizzes, getQuizHistory } from "@/lib/api/community";
import QuizCard from "@/components/community/QuizCard";
import QuizHistoryList from "@/components/community/QuizHistoryList";
import type { QuizAnswerResponse, QuizAttemptHistoryItem, QuizResponse } from "@/types/community";

const DAILY_LIMIT = 5;
const BASE_DATE = new Date("2026-06-01");

function getDayNumber(quizDate: string): number {
  const diff = Math.round(
    (new Date(quizDate).getTime() - BASE_DATE.getTime()) / (1000 * 60 * 60 * 24)
  );
  return diff + 1;
}

type Tab = "quiz" | "history";

export default function CommunityQuizPage() {
  const [tab, setTab] = useState<Tab>("quiz");

  // 오늘의 퀴즈 상태
  const [queue, setQueue] = useState<QuizResponse[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answeredOffset, setAnsweredOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalAnswered, setTotalAnswered] = useState(0);
  const [totalPoints, setTotalPoints] = useState(0);
  const [done, setDone] = useState(false);

  // 지난 퀴즈 상태
  const [history, setHistory] = useState<QuizAttemptHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    const todayStr = new Date().toISOString().slice(0, 10);

    Promise.all([getAvailableQuizzes(), getQuizHistory({ size: DAILY_LIMIT })])
      .then(([quizzes, todayHistory]) => {
        const today = todayHistory.filter((a) => a.attempted_at.slice(0, 10) === todayStr);
        const offset = today.length;
        const points = today.reduce((sum, a) => sum + a.points_earned, 0);

        setAnsweredOffset(offset);
        setTotalAnswered(offset);
        setTotalPoints(points);

        if (quizzes.length === 0) setDone(true);
        else setQueue(quizzes);
      })
      .catch(() => setError("퀴즈를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab !== "history") return;
    setHistoryLoading(true);
    getQuizHistory({ size: 100 })
      .then(setHistory)
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, [tab]);

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
  const displayNumber = answeredOffset + currentIndex + 1;

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto w-full">
      <h1 className="text-2xl font-black text-text-primary">건강 퀴즈</h1>

      {/* 탭 */}
      <div className="flex w-fit gap-1 rounded-2xl bg-gray-100 p-1">
        {(
          [
            ["quiz", "오늘의 퀴즈"],
            ["history", "지난 퀴즈"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={[
              "rounded-xl px-4 py-2 text-sm font-semibold transition-all",
              tab === key ? "bg-white text-gray-900 shadow-sm" : "text-gray-500",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="w-full">
        {/* 오늘의 퀴즈 탭 */}
        {tab === "quiz" && (
          <>
            {loading && (
              <p className="py-16 text-center text-sm text-text-secondary">퀴즈 불러오는 중...</p>
            )}
            {error && <p className="py-16 text-center text-sm text-text-secondary">{error}</p>}
            {done && (
              <div className="flex flex-col items-center gap-3 rounded-3xl bg-brand p-8 text-center">
                <p className="text-4xl">🎉</p>
                <p className="text-xl font-black text-gray-900">오늘 퀴즈 완료!</p>
                <p className="text-sm text-gray-700">
                  총 {totalAnswered}문제 · +{totalPoints}P 획득
                </p>
                <p className="mt-1 text-xs text-gray-500">내일 새로운 퀴즈가 기다리고 있어요.</p>
                <button
                  className="mt-2 text-sm text-gray-600 underline underline-offset-2"
                  onClick={() => setTab("history")}
                >
                  지난 퀴즈 보기 →
                </button>
              </div>
            )}
            {!loading && !error && !done && current && (
              <>
                <div className="mb-3 flex items-center justify-between px-1">
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
          </>
        )}

        {/* 지난 퀴즈 탭 */}
        {tab === "history" &&
          (historyLoading ? (
            <p className="py-16 text-center text-sm text-text-secondary">불러오는 중...</p>
          ) : (
            <QuizHistoryList history={history} />
          ))}
      </div>
    </div>
  );
}
