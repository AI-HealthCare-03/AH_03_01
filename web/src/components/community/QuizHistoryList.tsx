"use client";

import type { QuizAttemptHistoryItem, QuizCategory } from "@/types/community";

const CATEGORY_LABEL: Record<QuizCategory, string> = {
  BLOOD_SUGAR: "당뇨",
  BLOOD_PRESSURE: "고혈압",
  DIET: "식이",
  EXERCISE: "운동",
  GENERAL: "일반",
};

interface Props {
  history: QuizAttemptHistoryItem[];
}

export default function QuizHistoryList({ history }: Props) {
  const total = history.length;
  const correct = history.filter((h) => h.is_correct).length;
  const totalPoints = history.reduce((sum, h) => sum + h.points_earned, 0);
  const rate = total > 0 ? Math.round((correct / total) * 100) : 0;

  if (total === 0) {
    return (
      <p className="py-16 text-center text-sm text-text-secondary">아직 푼 퀴즈가 없습니다.</p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 통계 카드 */}
      <div className="rounded-3xl bg-brand p-5 grid grid-cols-4 gap-2 text-center">
        <div>
          <p className="text-2xl font-black text-gray-900">{total}</p>
          <p className="mt-0.5 text-xs text-gray-600">총 문제</p>
        </div>
        <div>
          <p className="text-2xl font-black text-gray-900">{correct}</p>
          <p className="mt-0.5 text-xs text-gray-600">정답</p>
        </div>
        <div>
          <p className="text-2xl font-black text-gray-900">{rate}%</p>
          <p className="mt-0.5 text-xs text-gray-600">정답률</p>
        </div>
        <div>
          <p className="text-2xl font-black text-amber-600">+{totalPoints}P</p>
          <p className="mt-0.5 text-xs text-gray-600">획득 포인트</p>
        </div>
      </div>

      {/* 지난 퀴즈 목록 */}
      <div className="flex flex-col gap-2">
        {history.map((item, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-white px-4 py-3"
          >
            <span
              className={`mt-0.5 text-lg leading-none ${item.is_correct ? "text-green-500" : "text-red-400"}`}
            >
              {item.is_correct ? "✓" : "✗"}
            </span>
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                  {CATEGORY_LABEL[item.category] ?? item.category}
                </span>
                <span className="text-xs text-gray-400">{item.attempted_at.slice(0, 10)}</span>
              </div>
              <p className="line-clamp-2 text-sm leading-snug text-gray-800">{item.question}</p>
            </div>
            {item.points_earned > 0 && (
              <span className="whitespace-nowrap text-xs font-semibold text-amber-600">
                +{item.points_earned}P
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
