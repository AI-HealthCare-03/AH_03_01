"use client";

import { Suspense } from "react";
import { use } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useChallenge } from "@/hooks/queries/useChallenge";
import { useVerifications } from "@/hooks/queries/useVerifications";
import { useMe } from "@/hooks/queries/useMe";
import { useLeaveChallenge } from "@/hooks/queries/useLeaveChallenge";
import { useUpdateChallenge } from "@/hooks/queries/useUpdateChallenge";
import PersonalDetail from "@/components/challenges/detail/PersonalDetail";
import GroupDetail from "@/components/challenges/detail/GroupDetail";
import NonMemberDetail from "@/components/challenges/detail/NonMemberDetail";
import ShieldModal from "@/components/challenges/verify/ShieldModal";
import { useCreateVerification } from "@/hooks/queries/useCreateVerification";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { POINT_BALANCE_KEY } from "@/hooks/queries/usePointBalance";
import { WEEKLY_XP_KEY } from "@/hooks/queries/useWeeklyXp";

/* =========================================
   챌린지 상세 페이지 (10-C08 / 10-C09 / 10-C19)
   - 개인: PersonalDetail
   - 그룹 참여자: GroupDetail
   - 비참여자: NonMemberDetail
   ========================================= */

interface ChallengeDetailPageProps {
  params: Promise<{ id: string }>;
}

function ChallengeDetailContent({
  challengeId,
}: {
  challengeId: number;
}) {
  const searchParams = useSearchParams();
  const inviteCode = searchParams.get("invite") ?? undefined;
  const initialTab =
    (searchParams.get("tab") as "info" | "chat" | "members") ?? "info";

  const router = useRouter();
  const { showToast } = useToast();
  const qc = useQueryClient();

  const { data: challenge, isLoading, error } = useChallenge(challengeId);
  /* mine: true — 내 인증만 조회. 다른 멤버의 인증이 섞이면 verifiedDates/pendingDates 오탐 발생 */
  const { data: verificationsData } = useVerifications(challengeId, { mine: true });
  const { data: me } = useMe();

  const [shieldOpen, setShieldOpen] = useState(false);
  const shieldMutation = useCreateVerification();
  const leaveMutation = useLeaveChallenge();
  const updateMutation = useUpdateChallenge(challengeId);

  /* 인증 완료 날짜 목록 (APPROVED 상태만) */
  const verifiedDates =
    verificationsData?.items
      .filter((v) => v.status === "APPROVED")
      .map((v) => v.created_at.split("T")[0]) ?? [];

  /* AI 검증 대기 날짜 목록 (PENDING 상태) */
  const pendingDates =
    verificationsData?.items
      .filter((v) => v.status === "PENDING")
      .map((v) => v.created_at.split("T")[0]) ?? [];

  /* 오늘 체크 인증 실패 여부 (CHECK + checked=false → REJECTED) */
  const rejectedToday =
    verificationsData?.items.some(
      (v) => v.status === "REJECTED" && v.verified_at?.split("T")[0] === new Date().toLocaleDateString("sv")
    ) ?? false;

  /* 사진 인증 결과(완료/실패) 알림.
     verify 페이지가 PHOTO 제출 후 ?pending={verificationId} 로 돌려보내면,
     useVerifications 의 폴링이 ai_worker(SigLIP2) 판정 결과를 받아온다.
     PENDING → APPROVED/REJECTED 로 확정되는 순간 1회만 토스트로 결과를 띄운다. */
  const pendingId = searchParams.get("pending");
  const notifiedRef = useRef(false);
  useEffect(() => {
    if (!pendingId) return;
    const pid = parseInt(pendingId, 10);
    const v = verificationsData?.items.find((it) => it.id === pid);
    if (!v || v.status === "PENDING" || notifiedRef.current) return;
    notifiedRef.current = true;
    if (v.status === "APPROVED") {
      showToast("인증 완료! 사진이 챌린지에 맞게 확인되었어요 🎉", "success");
      /* AI 승인 시 포인트/XP 백엔드에서 지급됨 → GNB 포인트 즉시 반영 */
      qc.invalidateQueries({ queryKey: POINT_BALANCE_KEY });
      qc.invalidateQueries({ queryKey: WEEKLY_XP_KEY });
    } else {
      showToast(
        `인증 실패: ${v.rejection_reason ?? "사진이 챌린지와 맞지 않아요. 다시 시도해 주세요."}`,
        "error",
      );
    }
    /* ?pending 제거 — 새로고침/재진입 시 중복 알림 방지 */
    router.replace(`/challenges/${challengeId}`);
  }, [pendingId, verificationsData, challengeId, router, showToast, qc]);

  /* 로딩 */
  if (isLoading) {
    return (
      <div className="max-w-xl mx-auto px-5 py-6 space-y-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-28 bg-white rounded-[16px] border border-border animate-pulse"
          />
        ))}
      </div>
    );
  }

  /* 에러 */
  if (error || !challenge) {
    return (
      <div className="max-w-xl mx-auto px-5 py-16 text-center">
        <p className="text-3xl mb-3" aria-hidden="true">🔍</p>
        <p className="text-base font-bold text-text-primary mb-2">
          챌린지를 찾을 수 없어요
        </p>
        <p className="text-sm text-text-secondary mb-6">
          {error ? extractErrorMessage(error) : "존재하지 않는 챌린지입니다"}
        </p>
        <Link
          href="/challenges"
          className="text-sm font-semibold text-brand-black underline"
        >
          챌린지 목록으로
        </Link>
      </div>
    );
  }

  /* 방지권 사용 핸들러 */
  const handleShieldConfirm = () => {
    shieldMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "SHIELD",
          verified_date: new Date().toISOString().slice(0, 10),
          shield_inventory_id: 1, /* mock */
        },
        method: "SHIELD",
      },
      {
        onSuccess: () => {
          setShieldOpen(false);
          showToast("방지권이 사용되었어요!", "success");
        },
        onError: (err) => {
          setShieldOpen(false);
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  /* 그룹 챌린지 탈퇴 핸들러 */
  const handleLeave = () => {
    leaveMutation.mutate(challengeId, {
      onSuccess: () => {
        showToast("챌린지에서 탈퇴했어요.", "success");
        router.push("/challenges?tab=my");
      },
      onError: (err) => {
        showToast(extractErrorMessage(err), "error");
      },
    });
  };

  /* 그룹 챌린지 취소 핸들러 (방장 전용) — CANCELLED 로 상태 변경 */
  const handleCancel = () => {
    updateMutation.mutate({ status: "CANCELLED" }, {
      onSuccess: () => {
        showToast("챌린지를 취소했어요.", "info");
        router.push("/challenges?tab=my");
      },
      onError: (err) => {
        showToast(extractErrorMessage(err), "error");
      },
    });
  };

  /* 개인 챌린지 포기 핸들러 — 소프트 삭제 대신 CANCELLED 로 상태 변경 */
  const handleQuit = () => {
    updateMutation.mutate({ status: "CANCELLED" }, {
      onSuccess: () => {
        showToast("챌린지를 포기했어요.", "info");
        router.push("/challenges?tab=my");
      },
      onError: (err) => {
        showToast(extractErrorMessage(err), "error");
      },
    });
  };

  /* 참가 완료 핸들러 */
  const handleJoined = () => {
    router.refresh();
  };

  /* 비참여자 여부: 백엔드가 is_member 필드를 내려줌 */
  const isNonMember = challenge.is_member === false;
  const isPrivate = challenge.visibility === "PRIVATE";

  return (
    <>
      {isNonMember ? (
        <NonMemberDetail
          challenge={challenge}
          inviteCode={inviteCode}
          requiresCode={isPrivate}
          onJoined={handleJoined}
        />
      ) : challenge.scope === "GROUP" ? (
        <GroupDetail
          challenge={challenge}
          onShield={() => setShieldOpen(true)}
          initialTab={initialTab}
          onLeave={handleLeave}
          onCancel={handleCancel}
          currentUserId={me?.id}
        />
      ) : (
        <PersonalDetail
          challenge={challenge}
          verifiedDates={verifiedDates}
          pendingDates={pendingDates}
          rejectedToday={rejectedToday}
          onShield={() => setShieldOpen(true)}
          onQuit={handleQuit}
        />
      )}

      {/* 실패 방지권 모달 */}
      <ShieldModal
        open={shieldOpen}
        onClose={() => setShieldOpen(false)}
        onConfirm={handleShieldConfirm}
        loading={shieldMutation.isPending}
      />
    </>
  );
}

export default function ChallengeDetailPage({
  params,
}: ChallengeDetailPageProps) {
  const { id } = use(params);
  const challengeId = parseInt(id, 10);

  return (
    <Suspense
      fallback={
        <div className="max-w-xl mx-auto px-5 py-6 space-y-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-28 bg-white rounded-[16px] border border-border animate-pulse"
            />
          ))}
        </div>
      }
    >
      <ChallengeDetailContent challengeId={challengeId} />
    </Suspense>
  );
}
