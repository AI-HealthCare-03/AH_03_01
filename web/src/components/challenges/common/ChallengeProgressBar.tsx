"use client";

/* =========================================
   챌린지 진행률 바
   ========================================= */

interface ChallengeProgressBarProps {
  progress: number;  /* 0~100 */
  completedDays?: number;
  totalDays?: number;
  showLabel?: boolean;
  height?: "sm" | "md";
}

export default function ChallengeProgressBar({
  progress,
  completedDays,
  totalDays,
  showLabel = true,
  height = "sm",
}: ChallengeProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const heightClass = height === "sm" ? "h-2" : "h-3";

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-text-secondary">달성률</span>
          <span className="text-xs font-semibold text-text-primary">
            {completedDays !== undefined && totalDays !== undefined
              ? `${completedDays}/${totalDays}일`
              : `${Math.round(clampedProgress)}%`}
          </span>
        </div>
      )}
      <div
        className={`w-full bg-surface rounded-full overflow-hidden ${heightClass}`}
        role="progressbar"
        aria-valuenow={Math.round(clampedProgress)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`달성률 ${Math.round(clampedProgress)}%`}
      >
        <div
          className="h-full bg-brand rounded-full transition-all duration-500"
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
}
