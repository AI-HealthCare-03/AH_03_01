"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import InviteUserModal from "@/components/challenges/detail/InviteUserModal";
import { useToast } from "@/components/ui/Toast";
import { useQuery } from "@tanstack/react-query";
import { fetchChallengeFeed } from "@/lib/api/challenge";
import type { Challenge } from "@/types/challenge";
import type { ChallengeParticipant } from "@/types/challenge";

/* =========================================
   그룹 챌린지 - 정보 탭 (10-C09)
   ========================================= */

interface GroupInfoTabProps {
  challenge: Challenge;
  participants: ChallengeParticipant[];
  currentUserId?: string;
  onLeave?: () => void;
  onCancel?: () => void;
  onShield?: () => void;
  verifiedDates?: string[];
  pendingDates?: string[];
  rejectedToday?: boolean;
}

function getInitial(name?: string): string {
  if (!name) return "?";
  return name.charAt(0).toUpperCase();
}

/* 날짜 범위 생성 (start_date ~ end_date, 오늘 이후 제외) */
function buildDateRange(start: string, end: string): string[] {
  const dates: string[] = [];
  const todayStr = new Date().toLocaleDateString("sv"); /* YYYY-MM-DD KST */
  const cur = new Date(start);
  const endDate = new Date(end < todayStr ? end : todayStr);
  while (cur <= endDate) {
    dates.push(cur.toLocaleDateString("sv"));
    cur.setDate(cur.getDate() + 1);
  }
  return dates;
}

export default function GroupInfoTab({
  challenge,
  participants,
  currentUserId,
  onLeave,
  onCancel,
  onShield,
  verifiedDates = [],
  pendingDates = [],
  rejectedToday = false,
}: GroupInfoTabProps) {
  const { showToast } = useToast();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);

  /* 합산 인증 내역 — 모달 열릴 때만 fetch (피드: 전체 참여자 APPROVED 인증 반환) */
  const { data: feedData, isLoading: historyLoading } = useQuery({
    queryKey: ["challenge-feed-history", challenge.id],
    queryFn: () => fetchChallengeFeed(challenge.id, 1, 200),
    enabled: historyOpen,
    staleTime: 30_000,
  });

  /* 날짜별 인증 수 — 피드는 APPROVED만 포함 */
  const verifiedByDate = useMemo(() => {
    const map: Record<string, number> = {};
    (feedData?.items ?? []).forEach((v) => {
      const d = v.verified_date;
      map[d] = (map[d] ?? 0) + 1;
    });
    return map;
  }, [feedData]);

  const dateRange = useMemo(
    () => buildDateRange(challenge.start_date, challenge.end_date),
    [challenge.start_date, challenge.end_date]
  );

  /* 현재 사용자가 방장인지 확인 */
  const myParticipant = currentUserId ? participants.find((p) => p.user_id === currentUserId) : undefined;
  const isOwner = myParticipant?.role === "OWNER";
  const canLeave = !!onLeave && !isOwner && challenge.status !== "COMPLETED";
  const canCancel = !!onCancel && isOwner && challenge.status !== "COMPLETED";
  const participantUserIds = participants
    .map((p) => p.user_id ?? p.user?.id)
    .filter((id): id is string => typeof id === "string");
  /* 모집 중 + 슬롯 여유 있을 때만 초대 활성 */
  const canInvite =
    challenge.status === "RECRUITING" &&
    participants.length < (challenge.max_participants ?? participants.length);

  // APPROVED 멤버에 한해, 시작일 지났으면 모집 중이라도 인증 가능
  const todayStr = new Date().toLocaleDateString("sv");
  const canVerify =
    myParticipant?.status === "APPROVED" &&
    (challenge.status === "ACTIVE" ||
      (challenge.status === "RECRUITING" && challenge.start_date <= todayStr));

  /* 오늘 인증 상태 — PersonalDetail 과 동일한 패턴 */
  const verifiedToday = verifiedDates.includes(todayStr);
  const pendingToday  = pendingDates.includes(todayStr);

  const handleCopyCode = async () => {
    if (!challenge.invite_code) return;
    try {
      await navigator.clipboard.writeText(challenge.invite_code);
      showToast("초대 코드가 복사되었어요!", "success");
    } catch {
      showToast(`초대 코드: ${challenge.invite_code}`, "info");
    }
  };

  /* 통계 */
  const totalVerified = participants.reduce(
    (sum, p) => sum + (p.progress_days ?? 0),
    0
  );
  const crisisCount = participants.filter(
    (p) => (p.missed_count ?? 0) >= 1
  ).length;

  const isCompleted = challenge.status === "COMPLETED";
  /* 획득한 보상 = 200P / 참여자 수 (그룹은 분배) */
  const rewardPerPerson = participants.length > 0
    ? Math.floor(200 / participants.length)
    : 200;

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

      {/* 인증 카드 — 인증 가능 상태일 때만 노출 */}
      {canVerify && (
        <div className="bg-white border border-border rounded-[14px] p-5 space-y-3">
          <p className="text-sm font-bold text-text-primary">오늘의 인증</p>
          {verifiedToday ? (
            <div className="flex items-center gap-2 py-3 bg-status-success-bg rounded-[12px] px-4">
              <span className="text-xl" aria-hidden="true">✅</span>
              <p className="text-sm font-semibold text-status-success">
                인증 완료!
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
            <>
              <Link href={`/challenges/${challenge.id}/verify`}>
                <Button variant="primary" size="md" fullWidth>
                  오늘 인증하기
                </Button>
              </Link>
              {onShield && (
                <button
                  type="button"
                  onClick={onShield}
                  className="w-full text-xs text-text-tertiary hover:text-text-secondary underline"
                >
                  🛡️ 방지권 사용
                </button>
              )}
            </>
          )}
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

        {/* 합산 인증 수 — 클릭 시 날짜별 내역 */}
        <button
          type="button"
          onClick={() => setHistoryOpen(true)}
          className="bg-white border border-border rounded-[14px] p-4 text-center hover:border-brand-black transition-colors group"
          aria-label="날짜별 인증 내역 보기"
        >
          <p className="text-2xl font-black text-text-primary group-hover:text-brand-black transition-colors">
            {totalVerified}
          </p>
          <p className="text-xs text-text-tertiary mt-1 flex items-center justify-center gap-1">
            합산 인증 수
            <span className="text-[10px] text-text-disabled">›</span>
          </p>
        </button>

        <div className="bg-white border border-border rounded-[14px] p-4 text-center">
          <p className="text-2xl font-black text-brand-black">
            {isCompleted ? rewardPerPerson : 200} P
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            {isCompleted ? "획득한 보상" : "예상 보상"}
          </p>
          {isCompleted && participants.length > 1 && (
            <p className="text-[10px] text-text-disabled mt-0.5">
              200P ÷ {participants.length}명
            </p>
          )}
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

      {/* 날짜별 인증 내역 모달 */}
      {historyOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end md:items-center justify-center"
          role="dialog"
          aria-modal="true"
          aria-label="날짜별 인증 내역"
        >
          {/* 배경 오버레이 */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setHistoryOpen(false)}
          />
          {/* 시트 */}
          <div className="relative w-full max-w-lg bg-white rounded-t-[20px] md:rounded-[20px] px-5 pt-5 pb-8 max-h-[70vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <p className="text-base font-black text-text-primary">날짜별 인증 내역</p>
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="text-text-tertiary hover:text-text-primary text-xl leading-none"
                aria-label="닫기"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-text-tertiary mb-4">
              {challenge.start_date} ~ {challenge.end_date} · 참여자 {participants.length}명
            </p>

            {historyLoading ? (
              <div className="space-y-2 overflow-y-auto">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="h-10 bg-surface rounded-[10px] animate-pulse" />
                ))}
              </div>
            ) : dateRange.length === 0 ? (
              <p className="text-sm text-text-secondary text-center py-8">아직 인증 기간이 시작되지 않았어요</p>
            ) : (
              <div className="overflow-y-auto space-y-2">
                {[...dateRange].reverse().map((date) => {
                  const count = verifiedByDate[date] ?? 0;
                  const total = participants.length;
                  const allDone = count >= total;
                  return (
                    <div
                      key={date}
                      className="flex items-center justify-between px-4 py-2.5 rounded-[10px] bg-surface"
                    >
                      <span className="text-sm text-text-secondary">{date}</span>
                      <span
                        className={[
                          "text-sm font-semibold",
                          allDone ? "text-status-success" : count > 0 ? "text-brand-black" : "text-text-disabled",
                        ].join(" ")}
                      >
                        {count}/{total}명 인증
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 챌린지 탈퇴 */}
      {canLeave && (
        <div className="bg-white border border-border rounded-[14px] p-4">
          {confirmLeave ? (
            <div className="space-y-3">
              <p className="text-sm font-bold text-text-primary">정말 탈퇴하시겠어요?</p>
              <p className="text-xs text-text-secondary">탈퇴 후에도 챌린지 기록은 완료 탭에서 확인할 수 있어요.</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmLeave(false)}
                  className="flex-1 py-2 rounded-[10px] border border-border text-sm font-semibold text-text-secondary"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={onLeave}
                  className="flex-1 py-2 rounded-[10px] bg-status-danger text-white text-sm font-semibold"
                >
                  탈퇴하기
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmLeave(true)}
              className="w-full text-xs text-text-tertiary hover:text-status-danger underline py-1"
            >
              챌린지 탈퇴하기
            </button>
          )}
        </div>
      )}

      {/* 챌린지 취소 (방장 전용) */}
      {canCancel && (
        <div className="bg-white border border-border rounded-[14px] p-4">
          {confirmCancel ? (
            <div className="space-y-3">
              <p className="text-sm font-bold text-text-primary">정말 챌린지를 취소하시겠어요?</p>
              <p className="text-xs text-text-secondary">취소 후에는 되돌릴 수 없으며, 모든 멤버의 챌린지가 종료돼요.</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmCancel(false)}
                  className="flex-1 py-2 rounded-[10px] border border-border text-sm font-semibold text-text-secondary"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={onCancel}
                  className="flex-1 py-2 rounded-[10px] bg-status-danger text-white text-sm font-semibold"
                >
                  챌린지 취소하기
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmCancel(true)}
              className="w-full text-xs text-text-tertiary hover:text-status-danger underline py-1"
            >
              챌린지 취소하기
            </button>
          )}
        </div>
      )}

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
