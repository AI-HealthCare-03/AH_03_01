"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useChallengeParticipants } from "@/hooks/queries/useChallengeParticipants";
import { useMe } from "@/hooks/queries/useMe";
import { useChallenge } from "@/hooks/queries/useChallenge";
import { respondToPendingParticipant, kickParticipant } from "@/lib/api/challenge";
import { extractErrorMessage } from "@/lib/api/client";
import ReportModal from "@/components/community/ReportModal";

/* =========================================
   그룹 챌린지 - 멤버 탭
   - APPROVED: 이름 + 진행률 + (방장만) 탈퇴 버튼 + (타인에게) 신고 버튼
   - PENDING: 방장에게만 수락/거절 섹션
   ========================================= */

interface GroupMemberTabProps {
  challengeId: number;
  totalDays?: number;
}

function getInitial(name?: string): string {
  if (!name) return "?";
  return name.charAt(0).toUpperCase();
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

  const [kickConfirmUserId, setKickConfirmUserId] = useState<string | null>(null);
  const [reportTarget, setReportTarget] = useState<{ participantId: number } | null>(null);

  const items = data?.items ?? [];
  const approved = items.filter((p) => p.status === "APPROVED");
  const pending = items.filter((p) => p.status === "PENDING");
  const isOwner = !!me && !!challenge && (challenge as { creator_id?: string }).creator_id === me.id;

  const respondMutation = useMutation({
    mutationFn: ({ userId, action }: { userId: string; action: "approve" | "reject" }) =>
      respondToPendingParticipant(challengeId, userId, action),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: ["challenge-participants", challengeId] });
      showToast(vars.action === "approve" ? "참가를 수락했어요" : "참가를 거절했어요", "success");
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const kickMutation = useMutation({
    mutationFn: (targetUserId: string) => kickParticipant(challengeId, targetUserId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["challenge-participants", challengeId] });
      setKickConfirmUserId(null);
      showToast("멤버를 탈퇴시켰어요", "success");
    },
    onError: (err) => {
      setKickConfirmUserId(null);
      showToast(extractErrorMessage(err), "error");
    },
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
                respondMutation.isPending && respondMutation.variables?.userId === p.user_id;
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
                      <p className="text-sm font-semibold text-text-primary truncate">{name}</p>
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
                      loading={pendingThis && respondMutation.variables?.action === "reject"}
                      onClick={() => respondMutation.mutate({ userId: p.user_id, action: "reject" })}
                    >
                      거절
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      loading={pendingThis && respondMutation.variables?.action === "approve"}
                      onClick={() => respondMutation.mutate({ userId: p.user_id, action: "approve" })}
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
        {approved.length === 0 ? (
          <div className="py-10 text-center text-sm text-text-tertiary">
            아직 참여한 멤버가 없어요
          </div>
        ) : (
          <ul className="space-y-3">
            {approved.map((p) => {
              const name = p.user?.nickname ?? p.user?.name ?? `유저${p.user_id}`;
              const progress = p.progress_days ?? 0;
              const pct = totalDays && totalDays > 0 ? Math.round((progress / totalDays) * 100) : 0;
              const isCrisis = (p.missed_count ?? 0) >= 1;
              const isSelf = me?.id === p.user_id;
              const isKickConfirm = kickConfirmUserId === p.user_id;

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
                      <span className="text-sm font-semibold text-text-primary truncate">{name}</span>
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

                  {/* 액션 버튼 영역 */}
                  {!isSelf && (
                    <div className="flex gap-1 shrink-0">
                      {/* 신고 — 모든 멤버가 타인에게 가능 */}
                      <button
                        type="button"
                        onClick={() => setReportTarget({ participantId: p.id })}
                        className="text-[11px] text-text-tertiary hover:text-status-danger px-2 py-1 rounded-[6px] hover:bg-status-danger-bg transition-colors"
                      >
                        신고
                      </button>

                      {/* 탈퇴시키기 — 방장 전용 */}
                      {isOwner && (
                        isKickConfirm ? (
                          <div className="flex gap-1">
                            <button
                              type="button"
                              onClick={() => setKickConfirmUserId(null)}
                              className="text-[11px] text-text-tertiary px-2 py-1 rounded-[6px] border border-border"
                            >
                              취소
                            </button>
                            <button
                              type="button"
                              onClick={() => kickMutation.mutate(p.user_id)}
                              disabled={kickMutation.isPending}
                              className="text-[11px] text-white bg-status-danger px-2 py-1 rounded-[6px] disabled:opacity-50"
                            >
                              {kickMutation.isPending ? "처리 중" : "확인"}
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setKickConfirmUserId(p.user_id)}
                            className="text-[11px] text-text-tertiary hover:text-status-danger px-2 py-1 rounded-[6px] hover:bg-status-danger-bg transition-colors"
                          >
                            탈퇴
                          </button>
                        )
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* 신고 모달 */}
      {reportTarget && (
        <ReportModal
          targetType="CHALLENGE_PARTICIPANT"
          targetId={reportTarget.participantId}
          onClose={() => setReportTarget(null)}
        />
      )}
    </div>
  );
}
