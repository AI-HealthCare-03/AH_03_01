"use client";

import ChallengeCategoryIcon from "@/components/challenges/common/ChallengeCategoryIcon";
import ChallengeProgressBar from "@/components/challenges/common/ChallengeProgressBar";
import type { ChallengeSummaryResponse } from "@/types/challenge";

/* =========================================
   챌린지 요약 통계 컴포넌트
   ========================================= */

interface SummaryStatsProps {
  data: ChallengeSummaryResponse;
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
            <div
              key={item.challenge_id}
              className="bg-white border border-border rounded-[14px] p-4 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-3">
                <ChallengeCategoryIcon category={item.category} size="sm" />
                <p className="text-sm font-semibold text-text-primary flex-1 truncate">
                  {item.title}
                </p>
                <span className="text-xs font-bold text-brand-black shrink-0">
                  +{item.earned_points} P
                </span>
              </div>
              <ChallengeProgressBar
                progress={item.success_rate}
                completedDays={item.completed_days}
                totalDays={item.total_days}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
