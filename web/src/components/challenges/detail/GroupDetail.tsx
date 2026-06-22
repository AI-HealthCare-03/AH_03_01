"use client";

import { useState } from "react";
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
  onLeave?: () => void;
  onCancel?: () => void;
  currentUserId?: string;
  verifiedDates?: string[];
  pendingDates?: string[];
  rejectedToday?: boolean;
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
  onLeave,
  onCancel,
  currentUserId,
  verifiedDates = [],
  pendingDates = [],
  rejectedToday = false,
}: GroupDetailProps) {
  const [activeTab, setActiveTab] = useState<GroupTab>(initialTab);
  const { showToast } = useToast();
  const { data: participantsData } = useChallengeParticipants(challenge.id);

  const catConfig = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;
  const progressPct = challenge.achievement_rate ?? 0;

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
            <GroupInfoTab
              challenge={challenge}
              participants={participants}
              currentUserId={currentUserId}
              onLeave={onLeave}
              onCancel={onCancel}
              onShield={onShield}
              verifiedDates={verifiedDates}
              pendingDates={pendingDates}
              rejectedToday={rejectedToday}
            />
          )}
          {activeTab === "chat" && (
            <GroupChatTab challengeId={challenge.id} />
          )}
          {activeTab === "members" && (
            <GroupMemberTab
              challengeId={challenge.id}
            />
          )}
        </div>

      </div>
    </div>
  );
}
