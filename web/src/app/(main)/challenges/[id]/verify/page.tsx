"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useChallenge } from "@/hooks/queries/useChallenge";
import { useVerifications } from "@/hooks/queries/useVerifications";
import { useCreateVerification } from "@/hooks/queries/useCreateVerification";
import CheckVerify from "@/components/challenges/verify/CheckVerify";
import MeditationTimer from "@/components/challenges/verify/MeditationTimer";
import PhotoVerify from "@/components/challenges/verify/PhotoVerify";
import QuestionnaireVerify from "@/components/challenges/verify/QuestionnaireVerify";
import RewardCelebrationModal from "@/components/challenges/verify/RewardCelebrationModal";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { format } from "@/lib/dateUtils";

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
  /* mine: true — 내 인증만 조회. 다른 멤버의 인증이 섞이면 중복 인증 오탐 발생 */
  const { data: verificationsData, isLoading: isLoadingVerifications } = useVerifications(challengeId, { mine: true });
  const verifyMutation = useCreateVerification();

  const [rewardOpen, setRewardOpen] = useState(false);
  const [earnedPoints, setEarnedPoints] = useState<number | null>(null);

  /* 오늘 날짜 (YYYY-MM-DD, 로컬 기준) */
  const today = format(new Date(), "yyyy-MM-dd");

  /* 오늘 이미 인증했는지 확인 (내 인증만, APPROVED/PENDING/REJECTED 모두 포함)
     REJECTED도 포함 — 아니요 선택 후 재제출 시 백엔드 409 방지 */
  const alreadyVerifiedToday = verificationsData?.items.some(
    (v) => v.verified_date === today &&
           (v.status === "APPROVED" || v.status === "PENDING" || v.status === "REJECTED")
  ) ?? false;

  /* 체크 인증 */
  const handleCheck = (checked: boolean, caption?: string) => {
    verifyMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "CHECK",
          verified_date: today,
          checked,
          caption: caption || undefined,
        },
        method: "CHECK",
      },
      {
        onSuccess: (data) => {
          if (data.status === "APPROVED") {
            setEarnedPoints(data.earned_points ?? null);
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

  /* 설문형 인증 (당뇨발 등). 9문항 답변 → answers 에 저장 + checked=true 로 인증 */
  const handleQuestionnaire = (answers: Record<string, string>) => {
    verifyMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "CHECK",
          verified_date: today,
          checked: true, // 답변 자체로 인증 완료. 위험 신호 분석은 추후
          answers,
        },
        method: "CHECK",
      },
      {
        onSuccess: (data) => {
          if (data.status === "APPROVED") {
            setEarnedPoints(data.earned_points ?? null);
            setRewardOpen(true);
          } else {
            showToast("설문이 제출되었어요", "info");
            router.push(`/challenges/${challengeId}`);
          }
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      },
    );
  };

  /* 사진 인증. PhotoVerify 가 파일 업로드를 마치고 photoFileId 를 넘겨준다. */
  const handlePhoto = (caption: string, photoFileId: number) => {
    verifyMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "PHOTO",
          verified_date: today,
          photo_file_id: photoFileId,
          caption: caption || undefined,
        },
        method: "PHOTO",
      },
      {
        onSuccess: (data) => {
          if (data.status === "APPROVED") {
            setEarnedPoints(data.earned_points ?? null);
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

  /* 명상 타이머 인증 */
  const handleMeditation = (durationSeconds: number, caption?: string) => {
    verifyMutation.mutate(
      {
        body: {
          challenge_id: challengeId,
          method: "CHECK",
          verified_date: today,
          checked: true,
          caption: caption || undefined,
          duration_seconds: durationSeconds,
        },
        method: "CHECK",
      },
      {
        onSuccess: (data) => {
          if (data.status === "APPROVED") {
            setEarnedPoints(data.earned_points ?? null);
            setRewardOpen(true);
          } else {
            showToast("명상 인증이 처리되었어요", "info");
            router.push(`/challenges/${challengeId}`);
          }
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  const handleRewardClose = () => {
    setRewardOpen(false);
    router.push(`/challenges/${challengeId}`);
  };

  if (isLoading || isLoadingVerifications) {
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

  /* 오늘 이미 인증한 경우 — 보상 모달이 열려 있으면 건너뜀 */
  if (alreadyVerifiedToday && !rewardOpen) {
    return (
      <div className="max-w-md mx-auto px-5 py-16 text-center">
        <p className="text-5xl mb-4" aria-hidden="true">✅</p>
        <p className="text-lg font-black text-text-primary mb-2">
          오늘 챌린지 인증을 이미 했어요!
        </p>
        <p className="text-sm text-text-secondary mb-8">
          내일 다시 인증할 수 있어요.
        </p>
        <Link
          href={`/challenges/${challengeId}`}
          className="inline-block px-6 py-3 bg-brand rounded-[12px] text-sm font-bold text-brand-black"
        >
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

      {/* 인증 컴포넌트 분기.
          1) 설문 템플릿이 지정된 경우 (예: 당뇨발 9문항) → QuestionnaireVerify
          2) CHECK → 예/아니오
          3) PHOTO → 사진 업로드 */}
      {(() => {
        /* 명상 챌린지 → 타이머 */
        if (challenge.category === "MEDITATION") {
          return (
            <MeditationTimer
              challenge={challenge}
              onSubmit={handleMeditation}
              onCancel={() => router.push(`/challenges/${challengeId}`)}
              loading={verifyMutation.isPending}
            />
          );
        }
        const questionnaireTemplate = (challenge.goal_config as Record<string, unknown> | undefined)?.[
          "questionnaire_template"
        ];
        if (
          challenge.verification_type === "CHECK" &&
          typeof questionnaireTemplate === "string"
        ) {
          return (
            <QuestionnaireVerify
              challenge={challenge}
              template={questionnaireTemplate}
              onSubmit={handleQuestionnaire}
              loading={verifyMutation.isPending}
            />
          );
        }
        if (challenge.verification_type === "CHECK") {
          return (
            <CheckVerify
              challenge={challenge}
              onSubmit={handleCheck}
              loading={verifyMutation.isPending}
            />
          );
        }
        return (
          <PhotoVerify
            challenge={challenge}
            onSubmit={handlePhoto}
            loading={verifyMutation.isPending}
          />
        );
      })()}

      {/* 보상 모달 */}
      <RewardCelebrationModal
        open={rewardOpen}
        onClose={handleRewardClose}
        rewardType="daily"
        earnedPoints={earnedPoints}
      />
    </div>
  );
}
