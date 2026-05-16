"use client";

import { useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import ChallengeCategoryIcon, { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import ChallengeProgressBar from "@/components/challenges/common/ChallengeProgressBar";
import ChallengeStatusBadge from "@/components/challenges/common/ChallengeStatusBadge";
import GroupInfoTab from "./GroupInfoTab";
import GroupChatTab from "./GroupChatTab";
import GroupMemberTab from "./GroupMemberTab";
import { useChallengeParticipants } from "@/hooks/queries/useChallengeParticipants";
import { dDayLabel } from "@/lib/dateUtils";
import type { Challenge } from "@/types/challenge";

/* =========================================
   그룹 챌린지 상세 (10-C09 / 15-C03)
   정보 / 소통 / 멤버 3탭
   ========================================= */

type GroupTab = "info" | "chat" | "members";

interface GroupDetailProps {
  challenge: Challenge;
  onShield: () => void;
  initialTab?: GroupTab;
}

const TABS: { key: GroupTab; label: string }[] = [
  { key: "info", label: "정보" },
  { key: "chat", label: "소통" },
  { key: "members", label: "멤버" },
];

export default function GroupDetail({
  challenge,
  onShield,
  initialTab = "info",
}: GroupDetailProps) {
  const [activeTab, setActiveTab] = useState<GroupTab>(initialTab);
  const { showToast } = useToast();
  const { data: participantsData } = useChallengeParticipants(challenge.id);

  const catConfig = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;
  const progressPct =
    challenge.total_days && challenge.total_days > 0
      ? Math.round(((challenge.my_progress ?? 0) / challenge.total_days) * 100)
      : 0;

  const participants = participantsData?.items ?? [];

  /* 초대 코드 복사 */
  const handleCopyInviteCode = async () => {
    if (!challenge.invite_code) return;
    try {
      await navigator.clipboard.writeText(challenge.invite_code);
      showToast("초대 코드가 복사되었어요!", "success");
    } catch {
      showToast(`초대 코드: ${challenge.invite_code}`, "info");
    }
  };

  return (
    <div>
      {/* 공통 헤더 */}
      <div className="bg-white border-b border-border px-5 py-5 md:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-start gap-3 mb-4">
            <ChallengeCategoryIcon category={challenge.category} size="md" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <ChallengeStatusBadge scope="GROUP" status={challenge.status} />
                <span className="text-xs text-text-tertiary">
                  {dDayLabel(challenge.end_date)}
                </span>
              </div>
              <h1 className="text-base font-black text-text-primary leading-snug">
                {challenge.title}
              </h1>
              <p className="text-xs text-text-tertiary mt-1">
                {catConfig.label}
              </p>
            </div>
            {/* 데스크탑 초대 코드 복사 */}
            {challenge.invite_code && (
              <button
                type="button"
                onClick={handleCopyInviteCode}
                className="hidden md:flex items-center gap-1.5 text-xs font-semibold text-text-secondary border border-border rounded-[8px] px-3 py-1.5 hover:bg-surface transition-colors"
              >
                <span aria-hidden="true">🔗</span>
                초대 코드 복사
              </button>
            )}
          </div>
          <ChallengeProgressBar
            progress={progressPct}
            completedDays={challenge.my_progress}
            totalDays={challenge.total_days}
          />
          {/* 모바일 초대 코드 복사 */}
          {challenge.invite_code && (
            <button
              type="button"
              onClick={handleCopyInviteCode}
              className="md:hidden mt-3 flex items-center gap-1.5 text-xs font-semibold text-text-secondary"
            >
              <span aria-hidden="true">🔗</span>
              초대 코드 복사: {challenge.invite_code}
            </button>
          )}
        </div>
      </div>

      {/* 탭 */}
      <div className="bg-white border-b border-border sticky top-16 z-10">
        <div className="max-w-5xl mx-auto px-5 md:px-8">
          <div
            role="tablist"
            aria-label="챌린지 상세 탭"
            className="flex"
          >
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                role="tab"
                aria-selected={activeTab === key}
                onClick={() => setActiveTab(key)}
                className={[
                  "flex-1 py-3 text-sm font-semibold border-b-2 transition-colors",
                  activeTab === key
                    ? "border-brand-black text-text-primary"
                    : "border-transparent text-text-tertiary hover:text-text-secondary",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 콘텐츠 */}
      <div className="max-w-5xl mx-auto md:flex md:gap-6 px-5 py-5 md:px-8">
        {/* 메인 탭 콘텐츠 */}
        <div className="flex-1 min-w-0">
          {activeTab === "info" && (
            <GroupInfoTab challenge={challenge} participants={participants} />
          )}
          {activeTab === "chat" && (
            <GroupChatTab challengeId={challenge.id} />
          )}
          {activeTab === "members" && (
            <GroupMemberTab
              challengeId={challenge.id}
              totalDays={challenge.total_days}
            />
          )}
        </div>

        {/* 데스크탑 우측: 오늘 인증하기 사이드박스 */}
        {challenge.status === "ACTIVE" && (
          <aside className="hidden md:block w-56 shrink-0">
            <div className="bg-white border border-border rounded-[16px] p-5 sticky top-32 space-y-3">
              <p className="text-sm font-bold text-text-primary">오늘의 인증</p>
              <Link href={`/challenges/${challenge.id}/verify`}>
                <Button variant="primary" size="md" fullWidth>
                  오늘 인증하기
                </Button>
              </Link>
              <button
                type="button"
                onClick={onShield}
                className="w-full text-xs text-text-tertiary hover:text-text-secondary underline"
              >
                🛡️ 방지권 사용
              </button>
            </div>
          </aside>
        )}
      </div>

      {/* 모바일 하단 고정 CTA */}
      {challenge.status === "ACTIVE" && (
        <div className="md:hidden fixed bottom-16 left-0 right-0 bg-white border-t border-border px-5 py-3 z-20">
          <Link href={`/challenges/${challenge.id}/verify`}>
            <Button variant="primary" size="lg" fullWidth>
              오늘 인증하기
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
