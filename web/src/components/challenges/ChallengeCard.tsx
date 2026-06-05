"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { dDayLabel } from "@/lib/dateUtils";
import ChallengeCategoryIcon from "./common/ChallengeCategoryIcon";
import ChallengeProgressBar from "./common/ChallengeProgressBar";
import ChallengeStatusBadge from "./common/ChallengeStatusBadge";
import type { Challenge } from "@/types/challenge";

/* =========================================
   챌린지 카드 컴포넌트
   목록(10-C01), 검색(10-C02) 에서 사용
   ========================================= */

interface ChallengeCardProps {
  challenge: Challenge;
  showCTA?: boolean;
}

export default function ChallengeCard({
  challenge,
  showCTA = true,
}: ChallengeCardProps) {
  const router = useRouter();
  const progressPct =
    challenge.total_days && challenge.total_days > 0
      ? Math.round(((challenge.my_progress ?? 0) / challenge.total_days) * 100)
      : 0;

  const isCrisis = (challenge.missed_count ?? 0) >= 1;
  const dday = dDayLabel(challenge.end_date);

  // 그룹 ACTIVE → 인증하기 / 그룹 RECRUITING → 소통하기 / 개인 → 오늘 인증하기
  const ctaLabel =
    challenge.scope === "GROUP"
      ? challenge.status === "ACTIVE" ? "오늘 인증하기" : "소통하기"
      : "오늘 인증하기";
  const ctaHref =
    challenge.scope === "GROUP"
      ? challenge.status === "ACTIVE"
        ? `/challenges/${challenge.id}/verify`
        : `/challenges/${challenge.id}?tab=chat`
      : `/challenges/${challenge.id}/verify`;

  return (
    <Link
      href={`/challenges/${challenge.id}`}
      className="block bg-white rounded-[16px] border border-border shadow-sm hover:shadow-md transition-shadow p-4"
      aria-label={`${challenge.title} 챌린지 상세 보기`}
    >
      {/* 헤더 */}
      <div className="flex items-start gap-3 mb-3">
        <ChallengeCategoryIcon category={challenge.category} size="md" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <ChallengeStatusBadge
              scope={challenge.scope}
              status={challenge.status}
              isCrisis={isCrisis && challenge.status === "ACTIVE"}
            />
          </div>
          <p className="text-sm font-bold text-text-primary leading-snug line-clamp-2">
            {challenge.title}
          </p>
        </div>
        <span className="shrink-0 text-xs font-semibold text-text-tertiary">
          {dday}
        </span>
      </div>

      {/* 진행률 */}
      {challenge.status === "ACTIVE" && (
        <div className="mb-3">
          <ChallengeProgressBar
            progress={progressPct}
            completedDays={challenge.my_progress}
            totalDays={challenge.total_days}
          />
        </div>
      )}

      {/* 완료 상태 */}
      {challenge.status === "COMPLETED" && (
        <div className="mb-3 text-xs text-text-secondary">
          {challenge.my_progress ?? 0}/{challenge.total_days ?? 0}일 달성
        </div>
      )}

      {/* 하단 정보 + CTA */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-text-tertiary">
          <span>보상 200P</span>
          {challenge.scope === "GROUP" && challenge.max_participants && (
            <span>
              최대 {challenge.max_participants}명
            </span>
          )}
        </div>
        {showCTA && challenge.status === "ACTIVE" && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              router.push(ctaHref);
            }}
            className="text-xs font-semibold text-brand-black underline underline-offset-2"
            aria-label={`${challenge.title} ${ctaLabel}`}
          >
            {ctaLabel}
          </button>
        )}
      </div>
    </Link>
  );
}
