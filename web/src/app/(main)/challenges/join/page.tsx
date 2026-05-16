"use client";

import { Suspense } from "react";
import Link from "next/link";
import InviteCodeInput from "@/components/challenges/InviteCodeInput";
import ChallengeCard from "@/components/challenges/ChallengeCard";
import { useChallenges } from "@/hooks/queries/useChallenges";
import { useToast } from "@/components/ui/Toast";

/* =========================================
   챌린지 검색 / 코드 참가 (10-C02)
   - 코드 입력 → 검색 결과 카드에서 참가
   - 추천 그룹 챌린지 목록
   ========================================= */

function JoinContent() {
  const { showToast } = useToast();

  /* 그룹 모집중 챌린지 목록 */
  const { data, isLoading } = useChallenges({
    scope: "GROUP",
    status: "RECRUITING",
    size: 10,
  });

  const groupItems = data?.items ?? [];

  const handleCodeSubmit = (code: string) => {
    /*
     * 코드만으로 challenge_id를 알 수 없는 API 구조 한계.
     * 백엔드 ParticipantService.join_by_code는 invite_code만으로 찾을 수 있으므로,
     * 현재는 "카드에서 직접 참가" 흐름으로 안내.
     * 초대 링크(/challenges/[id]?invite=CODE)로 진입하면 자동 처리됨.
     */
    showToast(
      `코드 ${code}로 된 챌린지를 아래 목록에서 찾아 참가해주세요. 초대 링크로 바로 접속할 수도 있어요.`,
      "info"
    );
  };

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-6">
      {/* 헤더 */}
      <div>
        <Link
          href="/challenges"
          className="text-sm text-text-tertiary hover:text-text-secondary mb-3 inline-block"
        >
          ← 챌린지로
        </Link>
        <h1 className="text-xl font-black text-text-primary">챌린지 참가</h1>
        <p className="text-sm text-text-secondary mt-1">
          초대 코드를 입력하거나 그룹 챌린지에 참가해보세요
        </p>
      </div>

      {/* 코드 입력 */}
      <div className="bg-white border border-border rounded-[16px] p-5 shadow-sm">
        <p className="text-sm font-bold text-text-primary mb-3">
          초대 코드로 참가
        </p>
        <InviteCodeInput onSubmit={handleCodeSubmit} />
        <p className="text-xs text-text-tertiary mt-3">
          초대 링크를 받았다면 링크를 직접 클릭하면 자동으로 참가 화면이 열려요
        </p>
      </div>

      {/* 그룹 챌린지 목록 */}
      <div>
        <p className="text-sm font-bold text-text-primary mb-3">
          참가 가능한 그룹 챌린지
        </p>
        {isLoading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-32 bg-white rounded-[16px] border border-border animate-pulse"
              />
            ))}
          </div>
        ) : groupItems.length === 0 ? (
          <div className="py-10 text-center bg-white rounded-[16px] border border-dashed border-border">
            <p className="text-3xl mb-3" aria-hidden="true">
              👥
            </p>
            <p className="text-sm font-semibold text-text-secondary">
              현재 참가 가능한 그룹 챌린지가 없어요
            </p>
            <p className="text-xs text-text-tertiary mt-1">
              직접 그룹 챌린지를 만들어 보세요!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {groupItems.map((c) => (
              <ChallengeCard key={c.id} challenge={c} showCTA={false} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function JoinChallengePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-2xl mx-auto px-5 py-6">
          <div className="h-6 bg-surface rounded animate-pulse mb-4 w-40" />
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div
                key={i}
                className="h-28 bg-white rounded-[16px] border border-border animate-pulse"
              />
            ))}
          </div>
        </div>
      }
    >
      <JoinContent />
    </Suspense>
  );
}
