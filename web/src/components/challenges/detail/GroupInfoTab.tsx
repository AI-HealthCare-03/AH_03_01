"use client";

import { useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import InviteUserModal from "@/components/challenges/detail/InviteUserModal";
import { useToast } from "@/components/ui/Toast";
import type { Challenge } from "@/types/challenge";
import type { ChallengeParticipant } from "@/types/challenge";
import { calcDDay } from "@/lib/dateUtils";

/* =========================================
   그룹 챌린지 - 정보 탭 (10-C09)
   ========================================= */

interface GroupInfoTabProps {
  challenge: Challenge;
  participants: ChallengeParticipant[];
  onShield: () => void;
}

function getInitial(name?: string): string {
  if (!name) return "?";
  return name.charAt(0).toUpperCase();
}

export default function GroupInfoTab({
  challenge,
  participants,
  onShield,
}: GroupInfoTabProps) {
const { showToast } = useToast();
  const [inviteOpen, setInviteOpen] = useState(false);
  const participantUserIds = participants
    .map((p) => p.user_id ?? p.user?.id)
    .filter((id): id is string => typeof id === "string");
  /* 모집 중 + 슬롯 여유 있을 때만 초대 활성 */
  const canInvite =
    challenge.status === "RECRUITING" &&
    participants.length < (challenge.max_participants ?? participants.length);

  const handleCopyCode = async () => {
    if (!challenge.invite_code) return;
    try {
      await navigator.clipboard.writeText(challenge.invite_code);
      showToast("초대 코드가 복사되었어요!", "success");
    } catch {
      showToast(`초대 코드: ${challenge.invite_code}`, "info");
    }
  };
  const canVerify =
    (challenge.status === "ACTIVE" || (challenge.status === "RECRUITING" && calcDDay(challenge.start_date) <= 0)) &&
    calcDDay(challenge.end_date) >= 0;

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
      {/* 초대 코드 카드 — 방장/참여자에게만 노출됨 */}
      {challenge.invite_code && (
        <div className="bg-brand/10 border border-brand rounded-[14px] p-4 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-text-secondary mb-1">초대 코드</p>
            <p className="text-xl font-black tracking-widest text-brand-black truncate">
              {challenge.invite_code}
            </p>
            <p className="text-[11px] text-text-tertiary mt-1">
              친구에게 공유하면 챌린지에 참가할 수 있어요
            </p>
          </div>
          <button
            type="button"
            onClick={handleCopyCode}
            className="shrink-0 px-3 py-2 rounded-[10px] bg-brand-black text-white text-xs font-semibold hover:opacity-90"
            aria-label="초대 코드 복사"
          >
            📋 복사
          </button>
        </div>
      )}


      {/* 오늘의 인증 */}
      {canVerify && (
        <div className="bg-white border border-border rounded-[14px] p-4 space-y-3">
          <p className="text-sm font-bold text-text-primary">오늘의 인증</p>
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
              if (participant) {
                return (
                  <div
                    key={idx}
                    className="flex flex-col items-center gap-1"
                    aria-label={`참여자 ${name ?? idx + 1}`}
                  >
                    <div className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold bg-brand text-brand-black">
                      {getInitial(name)}
                    </div>
                    <span className="text-[10px] text-text-tertiary truncate max-w-[44px]">
                      {name ?? `유저${idx + 1}`}
                    </span>
                  </div>
                );
              }
              /* 빈 슬롯 — 모집 중일 때만 초대 버튼으로 활성화 */
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    if (canInvite) setInviteOpen(true);
                    else showToast("지금은 더 초대할 수 없어요", "info");
                  }}
                  className="flex flex-col items-center gap-1 group"
                  aria-label="친구 초대"
                  disabled={!canInvite}
                >
                  <div
                    className={[
                      "w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold",
                      "bg-surface border-2 border-dashed transition-colors",
                      canInvite
                        ? "border-border text-text-disabled group-hover:border-brand-black group-hover:text-brand-black"
                        : "border-border text-text-disabled cursor-not-allowed",
                    ].join(" ")}
                  >
                    +
                  </div>
                  <span className="text-[10px] text-text-tertiary truncate max-w-[44px]">
                    {canInvite ? "초대" : "빈자리"}
                  </span>
                </button>
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

      {/* 친구 초대 모달 */}
      <InviteUserModal
        challengeId={challenge.id}
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        excludeUserIds={participantUserIds}
      />
    </div>
  );
}
