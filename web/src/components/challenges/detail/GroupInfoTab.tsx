"use client";

import ChallengeProgressBar from "@/components/challenges/common/ChallengeProgressBar";
import ChallengeCategoryIcon, { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type { Challenge } from "@/types/challenge";
import type { ChallengeParticipant } from "@/types/challenge";
import { dDayLabel } from "@/lib/dateUtils";

/* =========================================
   그룹 챌린지 - 정보 탭 (10-C09)
   ========================================= */

interface GroupInfoTabProps {
  challenge: Challenge;
  participants: ChallengeParticipant[];
}

function getInitial(name?: string): string {
  if (!name) return "?";
  return name.charAt(0).toUpperCase();
}

export default function GroupInfoTab({
  challenge,
  participants,
}: GroupInfoTabProps) {
  const catConfig = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;
  const progressPct =
    challenge.total_days && challenge.total_days > 0
      ? Math.round(((challenge.my_progress ?? 0) / challenge.total_days) * 100)
      : 0;

  /* 통계 */
  const totalVerified = participants.reduce(
    (sum, p) => sum + (p.progress_days ?? 0),
    0
  );
  const crisisCount = participants.filter(
    (p) => (p.missed_count ?? 0) >= 1
  ).length;

  return (
    <div className="space-y-5">
      {/* 챌린지 기본 정보 카드 */}
      <div className="bg-surface rounded-[14px] p-4 space-y-3">
        <div className="flex items-center gap-3">
          <ChallengeCategoryIcon category={challenge.category} size="md" />
          <div>
            <p className="font-bold text-text-primary">{challenge.title}</p>
            <p className="text-xs text-text-tertiary">
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

      {/* 참여 멤버 5칸 */}
      <div>
        <p className="text-sm font-semibold text-text-primary mb-3">
          참여 멤버 ({participants.length}/{challenge.max_participants ?? 5}명)
        </p>
        <div className="flex gap-2">
          {Array.from({ length: challenge.max_participants ?? 5 }).map(
            (_, idx) => {
              const participant = participants[idx];
              const name =
                participant?.user?.nickname ??
                participant?.user?.name ??
                undefined;
              return (
                <div
                  key={idx}
                  className="flex flex-col items-center gap-1"
                  aria-label={
                    participant ? `참여자 ${name ?? idx + 1}` : "빈 슬롯"
                  }
                >
                  <div
                    className={[
                      "w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold",
                      participant
                        ? "bg-brand text-brand-black"
                        : "bg-surface border-2 border-dashed border-border text-text-disabled",
                    ].join(" ")}
                  >
                    {participant ? getInitial(name) : "+"}
                  </div>
                  <span className="text-[10px] text-text-tertiary truncate max-w-[44px]">
                    {participant ? (name ?? `유저${idx + 1}`) : "빈자리"}
                  </span>
                </div>
              );
            }
          )}
        </div>
      </div>

      {/* 달성률 통계 카드 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-border rounded-[14px] p-4 text-center">
          <p className="text-2xl font-black text-text-primary">
            {participants.length}
          </p>
          <p className="text-xs text-text-tertiary mt-1">달성 인원</p>
        </div>
        <div className="bg-white border border-border rounded-[14px] p-4 text-center">
          <p className="text-2xl font-black text-text-primary">
            {totalVerified}
          </p>
          <p className="text-xs text-text-tertiary mt-1">합산 인증 수</p>
        </div>
        <div className="bg-white border border-border rounded-[14px] p-4 text-center">
          <p className="text-2xl font-black text-brand-black">200 P</p>
          <p className="text-xs text-text-tertiary mt-1">예상 보상</p>
        </div>
        <div className="bg-white border border-border rounded-[14px] p-4 text-center">
          <p
            className={[
              "text-2xl font-black",
              crisisCount > 0 ? "text-status-danger" : "text-text-primary",
            ].join(" ")}
          >
            {crisisCount}
          </p>
          <p className="text-xs text-text-tertiary mt-1">실패 위기</p>
        </div>
      </div>
    </div>
  );
}
