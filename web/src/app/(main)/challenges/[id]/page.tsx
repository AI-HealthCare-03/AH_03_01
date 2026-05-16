"use client";

import { Suspense } from "react";
import { use } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useChallenge } from "@/hooks/queries/useChallenge";
import { useVerifications } from "@/hooks/queries/useVerifications";
import PersonalDetail from "@/components/challenges/detail/PersonalDetail";
import GroupDetail from "@/components/challenges/detail/GroupDetail";
import NonMemberDetail from "@/components/challenges/detail/NonMemberDetail";
import ShieldModal from "@/components/challenges/verify/ShieldModal";
import { useCreateVerification } from "@/hooks/queries/useCreateVerification";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { useState } from "react";
import { useRouter } from "next/navigation";

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

  const { data: challenge, isLoading, error } = useChallenge(challengeId);
  const { data: verificationsData } = useVerifications(challengeId);

  const [shieldOpen, setShieldOpen] = useState(false);
  const shieldMutation = useCreateVerification();

  /* 인증 완료 날짜 목록 (APPROVED 상태만) */
  const verifiedDates =
    verificationsData?.items
      .filter((v) => v.status === "APPROVED")
      .map((v) => v.created_at.split("T")[0]) ?? [];

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

  /* 참가 완료 핸들러 */
  const handleJoined = () => {
    router.refresh();
  };

  /* 비참여자 여부 판단:
   * 실제로는 백엔드가 403을 반환하거나 participants API로 확인해야 함.
   * 현재는 invite 쿼리 파라미터가 있으면 NonMember로 보여주는 간단 처리.
   * TODO: /challenges/{id}/participants?userId=me API로 정확히 판단 */
  const isNonMember = !!inviteCode;

  return (
    <>
      {isNonMember ? (
        <NonMemberDetail
          challenge={challenge}
          inviteCode={inviteCode}
          onJoined={handleJoined}
        />
      ) : challenge.scope === "GROUP" ? (
        <GroupDetail
          challenge={challenge}
          onShield={() => setShieldOpen(true)}
          initialTab={initialTab}
        />
      ) : (
        <PersonalDetail
          challenge={challenge}
          verifiedDates={verifiedDates}
          onShield={() => setShieldOpen(true)}
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
