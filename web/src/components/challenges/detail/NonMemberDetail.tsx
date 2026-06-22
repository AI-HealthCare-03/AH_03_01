"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import ChallengeCategoryIcon, { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import ChallengeStatusBadge from "@/components/challenges/common/ChallengeStatusBadge";
import ChallengeRewardGuideModal from "@/components/challenges/common/RewardGuideModal";
import { useJoinChallenge } from "@/hooks/queries/useJoinChallenge";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { dDayLabel } from "@/lib/dateUtils";
import { formatGoalDescription } from "@/lib/challengeGoal";
import type { Challenge } from "@/types/challenge";

/* =========================================
   비참여자 챌린지 상세 (10-C19 / 15-C04)
   - 정보 카드 + 참여 규칙 + 참가 신청
   - ?invite=CODE 쿼리로 들어왔으면 코드 자동 설정
   ========================================= */

interface NonMemberDetailProps {
  challenge: Challenge;
  inviteCode?: string;
  requiresCode?: boolean;
  onJoined: () => void;
}

export default function NonMemberDetail({
  challenge,
  inviteCode: initialInviteCode,
  requiresCode = false,
  onJoined,
}: NonMemberDetailProps) {
  const { showToast } = useToast();
  const joinMutation = useJoinChallenge();
  const [showRewardGuide, setShowRewardGuide] = useState(false);
  const [codeInput, setCodeInput] = useState(initialInviteCode ?? "");

  const inviteCode = requiresCode ? codeInput || undefined : (initialInviteCode ?? undefined);

  const catConfig = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;
  const goalDescription = formatGoalDescription(challenge);

  const handleJoin = () => {
    if (requiresCode && !codeInput) return;
    joinMutation.mutate(
      { challengeId: challenge.id, inviteCode },
      {
        onSuccess: () => {
          showToast("챌린지에 참가했어요!", "success");
          onJoined();
        },
        onError: (err) => {
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  return (
    <div className="max-w-xl mx-auto px-5 py-6 space-y-5">
      {/* 챌린지 정보 카드 */}
      <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
        <div className="flex items-start gap-3 mb-4">
          <ChallengeCategoryIcon category={challenge.category} size="lg" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <ChallengeStatusBadge
                scope={challenge.scope}
                status={challenge.status}
              />
            </div>
            <h1 className="text-base font-black text-text-primary leading-snug">
              {challenge.title}
            </h1>
            <p className="text-sm text-text-secondary mt-1">
              {catConfig.label} · {dDayLabel(challenge.end_date)}
            </p>
          </div>
        </div>

        {challenge.description && (
          <p className="text-sm text-text-secondary leading-relaxed">
            {challenge.description}
          </p>
        )}

        {/* 비공개 챌린지 — 초대 코드 입력 */}
        {requiresCode && (
          <div className="mt-3 space-y-1">
            <p className="text-xs text-text-tertiary">초대 코드를 입력해야 참가할 수 있어요</p>
            <input
              type="text"
              value={codeInput}
              onChange={(e) => setCodeInput(e.target.value.trim())}
              placeholder="초대 코드 입력"
              className="w-full border border-border rounded-[10px] px-3 py-2 text-sm font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-black"
            />
          </div>
        )}

        {/* 공개 챌린지 — 초대 코드 표시 (URL 파라미터로 전달된 경우) */}
        {!requiresCode && initialInviteCode && (
          <div className="mt-3 bg-surface rounded-[10px] px-4 py-2 flex items-center gap-2">
            <span className="text-xs text-text-tertiary">초대 코드</span>
            <code className="text-sm font-mono font-bold text-brand-black">
              {initialInviteCode}
            </code>
          </div>
        )}
      </div>

      {/* 챌린지 정보 */}
      <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
        <p className="text-sm font-bold text-text-primary mb-3">챌린지 정보</p>
        <dl className="space-y-2">
          {[
            { label: "카테고리", value: catConfig.label },
            goalDescription && { label: "목표", value: goalDescription },
            {
              label: "기간",
              value: `${challenge.start_date} ~ ${challenge.end_date}`,
            },
            {
              label: "인증 방식",
              value:
                challenge.verification_type === "CHECK"
                  ? "체크 인증"
                  : challenge.verification_type === "PHOTO"
                  ? "사진 인증"
                  : "방지권",
            },
            challenge.scope === "GROUP" && {
              label: "모집 인원",
              value:
                challenge.participant_count !== undefined
                  ? `${challenge.participant_count} / ${challenge.max_participants}명`
                  : `${challenge.max_participants}명`,
            },
          ]
            .filter(Boolean)
            .map((item) => {
              const row = item as { label: string; value: string };
              return (
                <div key={row.label} className="flex justify-between text-sm">
                  <dt className="text-text-tertiary">{row.label}</dt>
                  <dd className="font-semibold text-text-primary">
                    {row.value}
                  </dd>
                </div>
              );
            })}
        </dl>
      </div>

      {/* 예상 보상 */}
      <div className="bg-brand/10 border border-brand rounded-[16px] p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-bold text-brand-black">예상 보상</p>
          <button
            type="button"
            onClick={() => setShowRewardGuide(true)}
            className="text-xs text-text-tertiary underline"
          >
            보상 안내 보기
          </button>
        </div>
        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">데일리 인증 보상</span>
            <span className="font-bold">최대 100 P/일</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">완주 보너스</span>
            <span className="font-bold">200 P</span>
          </div>
        </div>
      </div>

      {/* 참여 신청 버튼 */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        onClick={handleJoin}
        loading={joinMutation.isPending}
        disabled={requiresCode && !codeInput}
      >
        챌린지 참가하기
      </Button>

      {/* 보상 안내 모달 */}
      <ChallengeRewardGuideModal
        open={showRewardGuide}
        onClose={() => setShowRewardGuide(false)}
      />
    </div>
  );
}
