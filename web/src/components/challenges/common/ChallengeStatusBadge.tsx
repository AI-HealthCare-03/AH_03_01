"use client";

import type { ChallengeStatus, ChallengeScope } from "@/types/challenge";

/* =========================================
   챌린지 상태/범위 배지
   ========================================= */

interface StatusBadgeProps {
  status?: ChallengeStatus;
  scope?: ChallengeScope;
  isCrisis?: boolean;
}

const STATUS_CONFIG: Record<ChallengeStatus, { label: string; className: string }> = {
  ACTIVE: { label: "진행중", className: "bg-status-success-bg text-status-success" },
  COMPLETED: { label: "완료", className: "bg-surface text-text-secondary" },
  CANCELLED: { label: "취소됨", className: "bg-status-danger-bg text-status-danger" },
  RECRUITING: { label: "모집중", className: "bg-status-info-bg text-status-info" },
};

const SCOPE_CONFIG: Record<ChallengeScope, { label: string; className: string }> = {
  PERSONAL: { label: "개인", className: "bg-surface text-text-secondary" },
  GROUP: { label: "그룹", className: "bg-brand-light text-brand-black" },
};

export default function ChallengeStatusBadge({
  status,
  scope,
  isCrisis = false,
}: StatusBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1">
      {isCrisis && (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-status-danger-bg text-status-danger">
          위기
        </span>
      )}
      {scope && (
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${SCOPE_CONFIG[scope].className}`}
        >
          {SCOPE_CONFIG[scope].label}
        </span>
      )}
      {status && (
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${STATUS_CONFIG[status].className}`}
        >
          {STATUS_CONFIG[status].label}
        </span>
      )}
    </span>
  );
}
