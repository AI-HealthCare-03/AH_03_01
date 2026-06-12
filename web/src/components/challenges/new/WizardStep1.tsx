"use client";

import type { ChallengeScope, ChallengeVisibility } from "@/types/challenge";

/* =========================================
   Step 1: 참여 방식 선택 (개인 / 그룹)
   ========================================= */

interface WizardStep1Props {
  value: ChallengeScope | null;
  onChange: (scope: ChallengeScope) => void;
  visibility: ChallengeVisibility;
  onVisibilityChange: (v: ChallengeVisibility) => void;
}

const SCOPE_OPTIONS: {
  value: ChallengeScope;
  emoji: string;
  title: string;
  desc: string;
}[] = [
  {
    value: "PERSONAL",
    emoji: "🧘",
    title: "혼자 도전",
    desc: "나만의 목표로 조용히 꾸준히",
  },
  {
    value: "GROUP",
    emoji: "👥",
    title: "같이 도전",
    desc: "친구와 함께 최대 5명까지",
  },
];

const VISIBILITY_OPTIONS: {
  value: ChallengeVisibility;
  emoji: string;
  title: string;
  desc: string;
}[] = [
  {
    value: "PUBLIC",
    emoji: "🌐",
    title: "공개",
    desc: "모집 중인 챌린지 목록에 표시돼요",
  },
  {
    value: "PRIVATE",
    emoji: "🔒",
    title: "비공개",
    desc: "초대 코드로만 참여할 수 있어요",
  },
];

export default function WizardStep1({
  value,
  onChange,
  visibility,
  onVisibilityChange,
}: WizardStep1Props) {
  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">참여 방식</h2>
      <p className="text-sm text-text-secondary mb-6">
        혼자 도전할까요, 함께 도전할까요?
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {SCOPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "flex flex-col items-center gap-3 p-6 rounded-[16px] border-2 transition-all duration-150",
              "text-left hover:shadow-md",
              value === opt.value
                ? "border-brand-black bg-white shadow-md"
                : "border-border bg-white hover:border-brand",
            ].join(" ")}
            aria-pressed={value === opt.value}
          >
            <span className="text-4xl" aria-hidden="true">
              {opt.emoji}
            </span>
            <div className="text-center">
              <p className="font-bold text-text-primary">{opt.title}</p>
              <p className="text-xs text-text-secondary mt-1">{opt.desc}</p>
            </div>
          </button>
        ))}
      </div>

      {/* 공개 설정 — 그룹 선택 시에만 표시 */}
      {value === "GROUP" && (
        <div className="mt-6">
          <p className="text-sm font-bold text-text-primary mb-3">공개 설정</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {VISIBILITY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => onVisibilityChange(opt.value)}
                className={[
                  "flex items-center gap-3 p-4 rounded-[12px] border-2 transition-all duration-150 text-left",
                  visibility === opt.value
                    ? "border-brand-black bg-white shadow-sm"
                    : "border-border bg-white hover:border-brand",
                ].join(" ")}
                aria-pressed={visibility === opt.value}
              >
                <span className="text-xl" aria-hidden="true">{opt.emoji}</span>
                <div>
                  <p className="text-sm font-bold text-text-primary">{opt.title}</p>
                  <p className="text-xs text-text-secondary mt-0.5">{opt.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
