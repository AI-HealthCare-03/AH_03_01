"use client";

import { useRouter, useSearchParams } from "next/navigation";

/* =========================================
   진행중 / 완료 / 추천 탭 컴포넌트
   ========================================= */

type TabKey = "active" | "completed" | "recommended";

const TABS: { key: TabKey; label: string }[] = [
  { key: "active", label: "진행중" },
  { key: "completed", label: "완료" },
  { key: "recommended", label: "추천" },
];

interface ChallengeListTabsProps {
  currentTab: TabKey;
}

export default function ChallengeListTabs({
  currentTab,
}: ChallengeListTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleTabChange = (tab: TabKey) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    router.replace(`/challenges?${params.toString()}`);
  };

  return (
    <div
      role="tablist"
      aria-label="챌린지 목록 탭"
      className="flex gap-1 bg-surface rounded-[12px] p-1"
    >
      {TABS.map(({ key, label }) => (
        <button
          key={key}
          role="tab"
          aria-selected={currentTab === key}
          onClick={() => handleTabChange(key)}
          className={[
            "flex-1 py-2 text-sm font-semibold rounded-[10px] transition-all duration-150",
            currentTab === key
              ? "bg-white text-text-primary shadow-sm"
              : "text-text-tertiary hover:text-text-secondary",
          ].join(" ")}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
