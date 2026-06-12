"use client";

import Link from "next/link";
import Button from "@/components/ui/Button";
import ChallengeCategoryIcon, { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import ChallengeProgressBar from "@/components/challenges/common/ChallengeProgressBar";
import ChallengeStatusBadge from "@/components/challenges/common/ChallengeStatusBadge";
import WeekStrip from "./WeekStrip";
import { dDayLabel, calcDDay, format } from "@/lib/dateUtils";
import type { Challenge } from "@/types/challenge";

/* =========================================
   개인 챌린지 상세 (10-C08)
   ========================================= */

interface PersonalDetailProps {
  challenge: Challenge;
  verifiedDates: string[];
  pendingDates?: string[];
  rejectedToday?: boolean;
  onShield: () => void;
}

export default function PersonalDetail({
  challenge,
  verifiedDates,
  pendingDates = [],
  rejectedToday = false,
  onShield,
}: PersonalDetailProps) {
  const catConfig = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;
  const progressPct =
    challenge.total_days && challenge.total_days > 0
      ? Math.round(((challenge.my_progress ?? 0) / challenge.total_days) * 100)
      : 0;

  /* 오늘 인증 여부 확인.
     toISOString() 은 UTC 기준이라 KST 자정 직후(00~09시)에는 하루 어긋나
     verifiedDates(백엔드가 +09:00 로 내려준 KST 일자)와 비교가 빗나간다.
     로컬 타임존 기준으로 today 를 만들어 비교한다. */
  const todayStr = format(new Date(), "yyyy-MM-dd");
  const verifiedToday = verifiedDates.includes(todayStr);
  const pendingToday  = pendingDates.includes(todayStr);

  return (
    <div className="max-w-xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 카드 */}
      <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
        <div className="flex items-start gap-3 mb-4">
          <ChallengeCategoryIcon category={challenge.category} size="md" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <ChallengeStatusBadge scope="PERSONAL" status={challenge.status} />
            </div>
            <h1 className="text-base font-black text-text-primary leading-snug">
              {challenge.title}
            </h1>
            <p className="text-xs text-text-tertiary mt-1">
              {catConfig.label} · {dDayLabel(challenge.end_date)}
            </p>
          </div>
        </div>
        <ChallengeProgressBar
          progress={progressPct}
          completedDays={challenge.my_progress}
          totalDays={challenge.total_days}
        />
      </div>

      {/* 오늘 인증 CTA */}
      {challenge.status === "ACTIVE" && calcDDay(challenge.end_date) >= 0 && (
        <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
          <p className="text-sm font-bold text-text-primary mb-3">
            오늘의 인증
          </p>
          {verifiedToday ? (
            <div className="flex items-center gap-2 py-3 bg-status-success-bg rounded-[12px] px-4">
              <span className="text-xl" aria-hidden="true">✅</span>
              <p className="text-sm font-semibold text-status-success">
                오늘 인증 완료!
              </p>
            </div>
          ) : pendingToday ? (
            <div className="flex items-center gap-2 py-3 bg-status-info-bg rounded-[12px] px-4">
              <span className="text-xl" aria-hidden="true">⏳</span>
              <p className="text-sm font-semibold text-status-info">
                AI 검증 중... 잠시만 기다려주세요
              </p>
            </div>
          ) : rejectedToday ? (
            <div className="flex items-center gap-2 py-3 bg-status-danger-bg rounded-[12px] px-4">
              <span className="text-xl" aria-hidden="true">❌</span>
              <p className="text-sm font-semibold text-status-danger">
                오늘 목표를 달성하지 못했어요
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <Link href={`/challenges/${challenge.id}/verify`}>
                <Button variant="primary" size="lg" fullWidth>
                  오늘 인증하기
                </Button>
              </Link>
              <button
                type="button"
                onClick={onShield}
                className="w-full text-xs text-text-tertiary hover:text-text-secondary underline py-1"
              >
                🛡️ 실패 방지권 사용하기
              </button>
            </div>
          )}
        </div>
      )}

      {/* 이번 주 달성 현황 */}
      <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
        <WeekStrip verifiedDates={verifiedDates} pendingDates={pendingDates} />
      </div>

      {/* 보상 정보 */}
      <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
        <p className="text-sm font-bold text-text-primary mb-3">보상</p>
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-secondary">
            {challenge.status === "COMPLETED" ? "획득한 보상" : "기간 완주 보상"}
          </span>
          <span className="font-bold text-brand-black">200 P</span>
        </div>
      </div>
    </div>
  );
}
