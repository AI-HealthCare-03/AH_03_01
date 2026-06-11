"use client";

import type { ReactNode } from "react";

interface WizardShellProps {
  currentStep: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  children: ReactNode;
}

const STEPS = [
  { num: 1, label: "신체 계측" },
  { num: 2, label: "혈압·혈당" },
  { num: 3, label: "가족력" },
  { num: 4, label: "흡연·음주" },
  { num: 5, label: "수면·운동" },
  { num: 6, label: "식습관" },
  { num: 7, label: "추가 정보" },
] as const;

export default function WizardShell({ currentStep, children }: WizardShellProps) {
  const progress = ((currentStep - 1) / (STEPS.length - 1)) * 100;
  /* 모바일에서는 스텝이 많아 번호+레이블 모두 표시하지 않고 진행바 + "X/7단계" 텍스트만 표시 */

  return (
    <div className="md:flex md:gap-8 max-w-4xl mx-auto">
      {/* 모바일: 상단 진행바 + 단계 텍스트 */}
      <div className="md:hidden mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-text-primary">
            {STEPS[currentStep - 1]?.label}
          </span>
          <span className="text-xs text-text-tertiary">
            {currentStep} / {STEPS.length}단계
          </span>
        </div>
        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-black rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 데스크탑: 좌측 스텝 인디케이터 */}
      <div className="hidden md:flex flex-col w-52 shrink-0 pt-4">
        <div className="space-y-0">
          {STEPS.map(({ num, label }, idx) => (
            <div key={num} className="flex flex-col">
              <div className="flex items-center gap-3">
                <div
                  className={[
                    "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0",
                    num < currentStep
                      ? "bg-brand-black text-white"
                      : num === currentStep
                      ? "bg-brand text-brand-black"
                      : "bg-surface text-text-tertiary border border-border",
                  ].join(" ")}
                >
                  {num < currentStep ? "✓" : num}
                </div>
                <div>
                  <p
                    className={[
                      "text-sm font-semibold",
                      num <= currentStep ? "text-text-primary" : "text-text-tertiary",
                    ].join(" ")}
                  >
                    {label}
                  </p>
                  <p className="text-xs text-text-tertiary">
                    {num === 1 ? "필수" : "선택"}
                  </p>
                </div>
              </div>
              {/* 연결선 */}
              {idx < STEPS.length - 1 && (
                <div
                  className={[
                    "ml-4 w-0.5 h-8 transition-colors",
                    num < currentStep ? "bg-brand-black" : "bg-border",
                  ].join(" ")}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 폼 영역 */}
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </div>
  );
}
