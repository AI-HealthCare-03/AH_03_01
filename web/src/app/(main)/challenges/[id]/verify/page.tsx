"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useChallenge } from "@/hooks/queries/useChallenge";
import { useCreateVerification } from "@/hooks/queries/useCreateVerification";
import CheckVerify from "@/components/challenges/verify/CheckVerify";
import PhotoVerify from "@/components/challenges/verify/PhotoVerify";
import RewardCelebrationModal from "@/components/challenges/verify/RewardCelebrationModal";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";

/* =========================================
   인증 페이지 (10-C10 / 10-C11)
   챌린지 verification_type 에 따라 분기
   ========================================= */

interface VerifyPageProps {
  params: Promise<{ id: string }>;
}

export default function VerifyPage({ params }: VerifyPageProps) {
  const { id } = use(params);
  const challengeId = parseInt(id, 10);
  const router = useRouter();
  const { showToast } = useToast();

  const { data: challenge, isLoading } = useChallenge(challengeId);
  const verifyMutation = useCreateVerification();

  const [rewardOpen, setRewardOpen] = useState(false);

  /* 체크 인증 */
  const handleCheck = (checked: boolean) => {
    verifyMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "CHECK",
          checked,
        },
        method: "CHECK",
      },
      {
        onSuccess: (data) => {
          if (data.status === "APPROVED") {
            setRewardOpen(true);
          } else {
            showToast("인증이 처리되었어요", "info");
            router.push(`/challenges/${challengeId}`);
          }
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  /* 사진 인증. PhotoVerify 가 파일 업로드를 마치고 photoFileId 를 넘겨준다. */
  const handlePhoto = (memo: string, photoFileId: number) => {
    verifyMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "PHOTO",
          photo_file_id: photoFileId,
          memo: memo || undefined,
        },
        method: "PHOTO",
      },
      {
        onSuccess: (data) => {
          if (data.status === "APPROVED") {
            setRewardOpen(true);
            return;
          }
          // PENDING: ai_worker 가 SigLIP2 로 분류 중. 상세 페이지에서 폴링.
          showToast("사진이 제출되었어요. AI가 검증 중이에요!", "info");
          router.push(`/challenges/${challengeId}?pending=${data.id}`);
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      },
    );
  };

  const handleRewardClose = () => {
    setRewardOpen(false);
    router.push(`/challenges/${challengeId}`);
  };

  if (isLoading) {
    return (
      <div className="max-w-md mx-auto px-5 py-10 space-y-4">
        <div className="h-16 bg-surface rounded-full animate-pulse mx-auto w-16" />
        <div className="h-8 bg-surface rounded animate-pulse" />
        <div className="h-32 bg-surface rounded-[16px] animate-pulse" />
      </div>
    );
  }

  if (!challenge) {
    return (
      <div className="max-w-md mx-auto px-5 py-16 text-center">
        <p className="text-sm text-text-tertiary">챌린지 정보를 불러올 수 없어요</p>
        <Link href="/challenges" className="mt-3 text-sm font-semibold text-brand-black underline block">
          챌린지로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-5 py-8">
      {/* 뒤로 가기 */}
      <Link
        href={`/challenges/${challengeId}`}
        className="text-sm text-text-tertiary hover:text-text-secondary mb-6 inline-block"
      >
        ← {challenge.title}
      </Link>

      {/* 인증 컴포넌트 분기 */}
      {challenge.verification_type === "CHECK" ? (
        <CheckVerify
          challenge={challenge}
          onSubmit={handleCheck}
          loading={verifyMutation.isPending}
        />
      ) : (
        <PhotoVerify
          challenge={challenge}
          onSubmit={handlePhoto}
          loading={verifyMutation.isPending}
        />
      )}

      {/* 보상 모달 */}
      <RewardCelebrationModal
        open={rewardOpen}
        onClose={handleRewardClose}
        rewardType="daily"
      />
    </div>
  );
}
