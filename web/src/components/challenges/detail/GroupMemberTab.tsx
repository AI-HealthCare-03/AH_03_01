"use client";

import { useChallengeParticipants } from "@/hooks/queries/useChallengeParticipants";
import ParticipantList from "./ParticipantList";

/* =========================================
   그룹 챌린지 - 멤버 탭
   ========================================= */

interface GroupMemberTabProps {
  challengeId: number;
  totalDays?: number;
}

export default function GroupMemberTab({
  challengeId,
  totalDays,
}: GroupMemberTabProps) {
  const { data, isLoading } = useChallengeParticipants(challengeId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-16 bg-surface rounded-[12px] animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <ParticipantList
      participants={data?.items ?? []}
      totalDays={totalDays}
    />
  );
}
