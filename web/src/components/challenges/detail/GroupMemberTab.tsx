"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useChallengeParticipants } from "@/hooks/queries/useChallengeParticipants";
import { useMe } from "@/hooks/queries/useMe";
import { useChallenge } from "@/hooks/queries/useChallenge";
import { respondToPendingParticipant } from "@/lib/api/challenge";
import { extractErrorMessage } from "@/lib/api/client";
import ParticipantList from "./ParticipantList";

/* =========================================
   그룹 챌린지 - 멤버 탭
   - APPROVED: 기존 ParticipantList 로 렌더
   - PENDING: 방장(creator_id === me.id) 에게만 별도 섹션 + 수락/거절 버튼
   ========================================= */

interface GroupMemberTabProps {
  challengeId: number;
  totalDays?: number;
}

export default function GroupMemberTab({
  challengeId,
  totalDays,
}: GroupMemberTabProps) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data, isLoading } = useChallengeParticipants(challengeId);
  const { data: me } = useMe();
  const { data: challenge } = useChallenge(challengeId);

  const items = data?.items ?? [];
  const approved = items.filter((p) => p.status === "APPROVED");
  const pending = items.filter((p) => p.status === "PENDING");
  const isOwner = !!me && !!challenge && (challenge as { creator_id?: string }).creator_id === me.id;

  const mutation = useMutation({
    mutationFn: ({ userId, action }: { userId: string; action: "approve" | "reject" }) =>
      respondToPendingParticipant(challengeId, userId, action),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: ["challenge-participants", challengeId] });
      showToast(vars.action === "approve" ? "참가를 수락했어요" : "참가를 거절했어요", "success");
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-16 bg-surface rounded-[12px] animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* 방장 전용: 참가 신청 대기 (PENDING) */}
      {isOwner && pending.length > 0 && (
        <section>
          <p className="text-xs font-bold text-text-secondary mb-2">
            참가 신청 ({pending.length})
          </p>
          <ul className="space-y-2">
            {pending.map((p) => {
              const name = p.user?.nickname ?? p.user?.name ?? `유저${p.user_id.slice(0, 6)}`;
              const pendingThis =
                mutation.isPending && mutation.variables?.userId === p.user_id;
              return (
                <li
                  key={p.id}
                  className="flex items-center justify-between gap-3 p-3 bg-status-warning-bg rounded-[12px] border border-status-warning/30"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-9 h-9 rounded-full bg-brand flex items-center justify-center text-sm font-bold shrink-0">
                      {name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-text-primary truncate">
                        {name}
                      </p>
                      <p className="text-[11px] text-text-tertiary">
                        {new Date(p.joined_at).toLocaleString("ko-KR", {
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })} 신청
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={pendingThis && mutation.variables?.action === "reject"}
                      onClick={() => mutation.mutate({ userId: p.user_id, action: "reject" })}
                    >
                      거절
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      loading={pendingThis && mutation.variables?.action === "approve"}
                      onClick={() => mutation.mutate({ userId: p.user_id, action: "approve" })}
                    >
                      수락
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {/* 참여 중인 멤버 (APPROVED) */}
      <section>
        {isOwner && pending.length > 0 && (
          <p className="text-xs font-bold text-text-secondary mb-2">
            참여 중인 멤버 ({approved.length})
          </p>
        )}
        <ParticipantList participants={approved} totalDays={totalDays} />
      </section>
    </div>
  );
}
