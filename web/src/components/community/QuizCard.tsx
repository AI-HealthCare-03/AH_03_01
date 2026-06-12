"use client";

import { useState } from "react";
import { answerQuiz } from "@/lib/api/community";
import type { QuizResponse, QuizAnswerResponse, QuizOption } from "@/types/community";

const CATEGORY_LABEL: Record<string, string> = {
  BLOOD_SUGAR: "당뇨",
  BLOOD_PRESSURE: "고혈압",
  DIET: "식이",
  EXERCISE: "운동",
  GENERAL: "일반",
};

const OPTIONS: { key: QuizOption; label: string }[] = [
  { key: "A", label: "①" },
  { key: "B", label: "②" },
  { key: "C", label: "③" },
  { key: "D", label: "④" },
];

interface Props {
  quiz: QuizResponse;
  dayNumber?: number;
  alreadyAnswered?: boolean;
  hasNext?: boolean;
  onAnswered?: (result: QuizAnswerResponse) => void;
  onNext?: () => void;
}

export default function QuizCard({
  quiz,
  dayNumber,
  alreadyAnswered = false,
  hasNext = false,
  onAnswered,
  onNext,
}: Props) {
  const [selected, setSelected] = useState<QuizOption | null>(null);
  const [result, setResult] = useState<QuizAnswerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitted = result !== null || alreadyAnswered;

  const optionText: Record<QuizOption, string> = {
    A: quiz.option_a,
    B: quiz.option_b,
    C: quiz.option_c,
    D: quiz.option_d,
  };

  function getOptionStyle(key: QuizOption): string {
    const base = "w-full text-left px-5 py-3.5 rounded-2xl border text-sm transition-all";

    if (!result) {
      return [
        base,
        selected === key
          ? "border-green-500 bg-white text-gray-900 font-medium"
          : "border-gray-200 bg-white text-gray-700 hover:border-gray-400",
      ].join(" ");
    }

    if (key === result.correct_option) {
      return `${base} border-green-500 bg-green-50 text-green-800 font-semibold`;
    }
    if (key === selected && !result.is_correct) {
      return `${base} border-red-400 bg-red-50 text-red-700`;
    }
    return `${base} border-gray-200 bg-white text-gray-400`;
  }

  async function handleSubmit() {
    if (!selected || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await answerQuiz(quiz.id, { selected_option: selected });
      setResult(res);
      onAnswered?.(res);
    } catch {
      setError("제출 중 오류가 발생했습니다. 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  }

  const dayLabel = dayNumber != null ? `Q${dayNumber}` : CATEGORY_LABEL[quiz.category] ?? quiz.category;

  return (
    <div className="rounded-3xl bg-brand p-6 flex flex-col gap-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold px-2.5 py-1 bg-white/60 rounded-full text-gray-700">
          {dayLabel} · {CATEGORY_LABEL[quiz.category] ?? quiz.category}
        </span>
        {result && result.points_earned > 0 && (
          <span className="text-sm font-bold text-gray-800">+{result.points_earned}P</span>
        )}
      </div>

      {/* 질문 */}
      <p className="text-xl font-black text-gray-900 leading-snug">{quiz.question}</p>

      {/* 보기 */}
      <div className="flex flex-col gap-2">
        {OPTIONS.map(({ key, label }) => (
          <button
            key={key}
            className={getOptionStyle(key)}
            onClick={() => !submitted && setSelected(key)}
            disabled={submitted}
          >
            {label} {optionText[key]}
            {result && key === result.correct_option && (
              <span className="ml-1.5 text-green-600">✓</span>
            )}
          </button>
        ))}
      </div>

      {/* 제출 / 다음 문제 버튼 */}
      {!submitted && (
        <button
          className="w-full py-4 rounded-2xl bg-gray-900 text-white font-bold text-base disabled:opacity-40 transition-opacity"
          onClick={handleSubmit}
          disabled={!selected || loading}
        >
          {loading ? "제출 중..." : "정답 확인"}
        </button>
      )}

      {result && (
        <button
          className="w-full py-4 rounded-2xl bg-gray-900 text-white font-bold text-base"
          onClick={onNext}
        >
          {hasNext ? "다음 문제 →" : "오늘 퀴즈 완료!"}
        </button>
      )}

      {error && <p className="text-sm text-red-600 text-center">{error}</p>}

      {/* 결과 피드백 */}
      {result && (
        <div
          className={[
            "rounded-2xl px-5 py-4 text-sm leading-relaxed",
            result.is_correct
              ? "bg-green-50 border border-green-200 text-green-800"
              : "bg-red-50 border border-red-200 text-red-800",
          ].join(" ")}
        >
          <p className="font-bold mb-1">{result.is_correct ? "🎉 정답입니다!" : "❌ 오답입니다."}</p>
          <p className="text-gray-700">{result.explanation}</p>
        </div>
      )}

      {alreadyAnswered && !result && (
        <p className="text-center text-sm text-gray-500">이미 답변한 퀴즈입니다.</p>
      )}
    </div>
  );
}
