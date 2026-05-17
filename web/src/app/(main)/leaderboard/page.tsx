"use client";

import Link from "next/link";
import LeaderboardCard from "@/components/challenges/ranking/LeaderboardCard";
import { useWeeklyLeaderboard } from "@/hooks/queries/useWeeklyXp";
import { useMe } from "@/hooks/queries/useMe";

/* =========================================
   주간 활동량(EXP) 리더보드
   GET /api/v1/leaderboards/weekly 실 연동
   ========================================= */

export default function LeaderboardPage() {
  const { data: me } = useMe();
  const { data, isLoading, isError } = useWeeklyLeaderboard(20);

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div>
        <Link
          href="/"
          className="text-sm text-text-tertiary hover:text-text-secondary mb-3 inline-block"
        >
          ← 홈으로
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-black text-text-primary">
            주간 활동 랭킹
          </h1>
          <span className="text-xs font-medium text-status-info bg-status-info-bg px-2 py-1 rounded-full">
            매주 월요일 00:00 리셋
          </span>
        </div>
        <p className="text-sm text-text-secondary mt-1">
          {data?.week_id ?? "—"} · 상위 3명에게 500 / 300 / 100 P를 차등
          지급해요
        </p>
      </div>

      {/* 내 순위 */}
      <div className="bg-brand/10 border border-brand rounded-[14px] px-4 py-3">
        <p className="text-xs font-semibold text-text-secondary mb-1">내 순위</p>
        <div className="flex items-center justify-between">
          <p className="text-2xl font-black text-brand-black">
            {data?.my_rank ? `${data.my_rank}위` : "—"}
          </p>
          <p className="text-sm font-semibold text-text-secondary">
            {(data?.my_points ?? 0).toLocaleString()} EXP
          </p>
        </div>
      </div>

      {/* 랭킹 목록 */}
      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-16 rounded-[14px] bg-surface animate-pulse"
            />
          ))}
        </div>
      ) : isError ? (
        <p className="text-sm text-text-tertiary text-center py-8">
          랭킹을 불러올 수 없어요
        </p>
      ) : data && data.entries.length > 0 ? (
        <div className="space-y-2">
          {data.entries.map((e) => (
            <LeaderboardCard
              key={e.user_id}
              rank={e.rank}
              name={e.user_name}
              exp={e.points}
              completedChallenges={0}
              isMe={!!me && e.user_id === me.id}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-text-tertiary text-center py-8">
          아직 이번 주 활동 기록이 없어요
        </p>
      )}

      {/* EXP 획득 방식 안내 */}
      <div className="bg-white border border-border rounded-[16px] p-5 shadow-sm">
        <p className="text-sm font-bold text-text-primary mb-3">
          활동량(EXP) 획득 방법 · 각 행위당 +10 EXP
        </p>
        <ul className="space-y-2">
          {[
            { icon: "📝", text: "건강 데이터 입력 (하루 1회)" },
            { icon: "📊", text: "건강 데이터 확인 — 위험도·추이·리포트 (하루 1회)" },
            { icon: "✅", text: "챌린지 인증" },
            { icon: "📰", text: "게시글 작성" },
            { icon: "💬", text: "댓글 작성" },
            { icon: "🧠", text: "퀴즈 풀기" },
          ].map((item) => (
            <li
              key={item.text}
              className="flex items-center justify-between text-sm"
            >
              <span className="flex items-center gap-2">
                <span aria-hidden="true">{item.icon}</span>
                <span className="text-text-secondary">{item.text}</span>
              </span>
              <span className="font-semibold text-brand-black">+10 EXP</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
