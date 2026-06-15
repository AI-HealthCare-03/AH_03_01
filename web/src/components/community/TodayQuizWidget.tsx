"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getAvailableQuizzes } from "@/lib/api/community";

export default function TodayQuizWidget() {
  const router = useRouter();
  const { data } = useQuery({
    queryKey: ["quizzes", "available"],
    queryFn: getAvailableQuizzes,
    staleTime: 1000 * 60 * 5,
  });

  const quiz = data?.[0];

  return (
    <div className="rounded-[16px] bg-brand p-4 flex flex-col gap-3">
      <p className="text-sm font-bold text-text-primary">💊 오늘의 퀴즈</p>
      {quiz ? (
        <>
          <p className="text-xs text-text-primary line-clamp-2 leading-snug">{quiz.question}</p>
          <button
            onClick={() => router.push("/community/quiz")}
            className="w-full py-2.5 rounded-[10px] bg-brand-black text-white text-sm font-bold hover:opacity-80 transition-opacity"
          >
            풀기 (+50P)
          </button>
        </>
      ) : (
        <p className="text-xs text-text-tertiary">오늘 퀴즈를 모두 풀었어요! 🎉</p>
      )}
    </div>
  );
}
