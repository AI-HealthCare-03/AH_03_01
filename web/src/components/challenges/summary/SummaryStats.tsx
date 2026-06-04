"use client";

import Link from "next/link";
import ChallengeCategoryIcon from "@/components/challenges/common/ChallengeCategoryIcon";
import ChallengeProgressBar from "@/components/challenges/common/ChallengeProgressBar";
import type {
  ChallengeSummaryResponse,
  ChallengeSummaryItem,
  GoalType,
} from "@/types/challenge";

/* =========================================
   챌린지 요약 통계 컴포넌트
   ========================================= */

interface SummaryStatsProps {
  data: ChallengeSummaryResponse;
}

/* 목표 텍스트 포매터 */
function formatGoal(goalType?: GoalType, goalValue?: number): string {
  if (!goalType || goalValue === undefined) return "";
  switch (goalType) {
    case "DURATION":
      return `${goalValue}분`;
    case "COUNT":
      return `${goalValue}회`;
    case "AMOUNT":
      return `${goalValue}`;
    case "CHECK":
      return "매일 체크";
    default:
      return "";
  }
}

/* 남은 일수 계산 */
function getRemainingDays(endDate?: string): number | null {
  if (!endDate) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(endDate);
  end.setHours(0, 0, 0, 0);
  return Math.ceil((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

/* 남은 일수 뱃지 스타일 */
function remainingStyle(days: number): string {
  if (days < 0) return "text-text-tertiary";
  if (days <= 3) return "text-status-error font-bold";
  if (days <= 7) return "text-status-warning font-semibold";
  return "text-text-secondary";
}

/* 남은 일수 텍스트 */
function remainingLabel(days: number): string {
  if (days < 0) return "종료됨";
  if (days === 0) return "오늘 마감";
  return `${days}일 남음`;
}

/* 챌린지 카드 */
function SummaryCard({ item }: { item: ChallengeSummaryItem }) {
  const goalText = formatGoal(item.goal_type, item.goal_value);
  const remaining = getRemainingDays(item.end_date);

  return (
    <Link
      href={`/challenges/${item.challenge_id}`}
      className="block bg-white border border-border rounded-[14px] p-4 shadow-sm hover:border-brand-black transition-colors"
    >
      {/* 제목 행 */}
      <div className="flex items-center gap-3 mb-1">
        <ChallengeCategoryIcon category={item.category} size="sm" />
        <p className="text-sm font-semibold text-text-primary flex-1 truncate">
          {item.title}
        </p>
        <span className="text-xs font-bold text-brand-black shrink-0">
          +{item.earned_points} P
        </span>
      </div>

      {/* 목표 + 남은 기간 */}
      <div className="flex items-center justify-between mb-3 ml-[calc(24px+12px)]">
        {goalText ? (
          <p className="text-xs text-text-tertiary">목표 {goalText}</p>
        ) : (
          <span />
        )}
        {remaining !== null && (
          <p className={`text-xs ${remainingStyle(remaining)}`}>
            {remainingLabel(remaining)}
          </p>
        )}
      </div>

      {/* 진행률 바 */}
      <ChallengeProgressBar
        progress={item.success_rate}
        completedDays={item.completed_days}
        totalDays={item.total_days}
      />
    </Link>
  );
}

export default function SummaryStats({ data }: SummaryStatsProps) {
  return (
    <div className="space-y-5">
      {/* 전체 통계 카드 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-border rounded-[14px] p-4 text-center shadow-sm">
          <p className="text-2xl font-black text-text-primary">
            {Math.round(data.average_success_rate)}%
          </p>
          <p className="text-xs text-text-tertiary mt-1">평균 달성률</p>
        </div>
        <div className="bg-white border border-brand rounded-[14px] p-4 text-center shadow-sm">
          <p className="text-2xl font-black text-brand-black">
            {data.total_earned_points.toLocaleString()} P
          </p>
          <p className="text-xs text-text-tertiary mt-1">획득 포인트</p>
        </div>
      </div>

      {/* 챌린지별 진행률 */}
      <div>
        <p className="text-sm font-bold text-text-primary mb-3">
          챌린지별 달성 현황
        </p>
        <div className="space-y-3">
          {data.items.map((item) => (
            <SummaryCard key={item.challenge_id} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
}
