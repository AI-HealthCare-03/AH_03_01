"use client";

import type { ReactNode } from "react";

/* =========================================
   위저드 쉘 (진행바 + 스텝 인디케이터)
   - 데스크탑: 좌측 스텝 인디케이터 + 우측 폼
   - 모바일: 상단 진행바 + 단일 컬럼
   ========================================= */

interface WizardShellProps {
  currentStep: number;
  totalSteps: number;
  stepLabels: string[];
  children: ReactNode;
  onBack?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  nextLoading?: boolean;
}

export default function WizardShell({
  currentStep,
  totalSteps,
  stepLabels,
  children,
  onBack,
  onNext,
  nextLabel = "다음",
  nextDisabled = false,
  nextLoading = false,
}: WizardShellProps) {
  const progressPct = ((currentStep - 1) / (totalSteps - 1)) * 100;

  return (
    <div className="min-h-screen bg-[#f8f8f8]" id="challenge-wizard-layout">
      {/* 모바일 상단 진행바 */}
      <div className="md:hidden bg-white border-b border-border px-5 pt-4 pb-3">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-text-tertiary">
            {currentStep} / {totalSteps} 단계
          </p>
          <p className="text-xs font-semibold text-text-primary">
            {stepLabels[currentStep - 1]}
          </p>
        </div>
        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-black rounded-full transition-all duration-400"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <div className="max-w-5xl mx-auto md:flex md:gap-8 px-5 py-6 md:px-8 md:py-10">
        {/* 데스크탑 좌측 스텝 인디케이터 */}
        <aside className="hidden md:block w-48 shrink-0">
          <div className="bg-white rounded-[16px] border border-border p-5 sticky top-24">
            <p className="text-xs font-bold text-text-tertiary uppercase tracking-wider mb-4">
              진행 단계
            </p>
            <ol className="space-y-3">
              {stepLabels.map((label, idx) => {
                const stepNum = idx + 1;
                const isCompleted = stepNum < currentStep;
                const isCurrent = stepNum === currentStep;
                const isFuture = stepNum > currentStep;
                return (
                  <li
                    key={stepNum}
                    className="flex items-center gap-3"
                    aria-current={isCurrent ? "step" : undefined}
                  >
                    <span
                      className={[
                        "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
                        isCompleted
                          ? "bg-brand-black text-white"
                          : isCurrent
                          ? "bg-brand text-brand-black border-2 border-brand-black"
                          : "bg-surface text-text-disabled",
                      ].join(" ")}
                    >
                      {isCompleted ? "✓" : stepNum}
                    </span>
                    <span
                      className={[
                        "text-sm",
                        isCurrent
                          ? "font-semibold text-text-primary"
                          : isFuture
                          ? "text-text-disabled"
                          : "text-text-secondary",
                      ].join(" ")}
                    >
                      {label}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        </aside>

        {/* 메인 폼 영역 */}
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-[16px] border border-border p-6 md:p-8">
            {children}

            {/* 네비게이션 버튼 */}
            <div className="flex gap-3 mt-8 pt-6 border-t border-border">
              {onBack && (
                <button
                  type="button"
                  onClick={onBack}
                  className="h-12 px-6 rounded-[12px] border border-border bg-white text-sm font-semibold text-text-secondary hover:bg-surface transition-colors"
                >
                  이전
                </button>
              )}
              {onNext && (
                <button
                  type="button"
                  onClick={onNext}
                  disabled={nextDisabled || nextLoading}
                  className={[
                    "flex-1 h-12 rounded-[12px] text-sm font-bold transition-all",
                    "disabled:opacity-40 disabled:cursor-not-allowed",
                    "bg-brand-black text-white hover:bg-[#333] active:scale-[0.98]",
                  ].join(" ")}
                >
                  {nextLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      처리 중...
                    </span>
                  ) : (
                    nextLabel
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
