"use client";

import type { ChallengeParticipant } from "@/types/challenge";

/* =========================================
   멤버 리스트 컴포넌트
   그룹 챌린지 멤버 탭에서 사용
   ========================================= */

interface ParticipantListProps {
  participants: ChallengeParticipant[];
  totalDays?: number;
}

function getInitial(name?: string): string {
  if (!name) return "?";
  return name.charAt(0).toUpperCase();
}

export default function ParticipantList({
  participants,
  totalDays,
}: ParticipantListProps) {
  if (participants.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-text-tertiary">
        아직 참여한 멤버가 없어요
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {participants.map((p) => {
        const name = p.user?.nickname ?? p.user?.name ?? `유저${p.user_id}`;
        const progress = p.progress_days ?? 0;
        const pct =
          totalDays && totalDays > 0
            ? Math.round((progress / totalDays) * 100)
            : 0;
        const isCrisis = (p.missed_count ?? 0) >= 1;

        return (
          <li
            key={p.id}
            className="flex items-center gap-3 p-3 bg-surface rounded-[12px]"
          >
            {/* 아바타 */}
            <div className="w-10 h-10 rounded-full bg-brand flex items-center justify-center text-sm font-bold shrink-0">
              {getInitial(name)}
            </div>

            {/* 이름 + 진행률 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-text-primary truncate">
                  {name}
                </span>
                {isCrisis && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-status-danger-bg text-status-danger shrink-0">
                    위기
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-black rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-text-tertiary shrink-0">
                  {progress}/{totalDays ?? "?"}일
                </span>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
