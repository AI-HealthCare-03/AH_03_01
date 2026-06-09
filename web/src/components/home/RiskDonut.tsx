"use client";

/* =========================================
   SVG 도넛 링 컴포넌트
   recharts 없이 circle 두 개로 구현
   ========================================= */

import type { RiskGrade } from "@/types/api";

interface RiskDonutProps {
  /** 0~100 점수 */
  score: number;
  grade: RiskGrade;
  /** 질병명 라벨 */
  label: string;
  /** 위험인자 개수 */
  riskFactorCount: number;
  size?: number;
}

/* 등급 → 색상 & 라벨. 백엔드는 RISK/HIGH_RISK 를 보내고 UI 초기 코드는 DANGER/HIGH_DANGER 를 쓰므로
   동일 표현으로 매핑한다. */
const RISK_STYLE = {
  color: "#e53935",
  badgeBg: "#ffeaea",
  badgeText: "#e53935",
  label: "위험",
} as const;

const HIGH_RISK_STYLE = {
  color: "#b71c1c",
  badgeBg: "#ffcdd2",
  badgeText: "#b71c1c",
  label: "고위험",
} as const;

const GRADE_CONFIG: Record<
  RiskGrade,
  { color: string; badgeBg: string; badgeText: string; label: string }
> = {
  NORMAL: {
    color: "#2e7d32",
    badgeBg: "#e8f5e9",
    badgeText: "#2e7d32",
    label: "정상",
  },
  CAUTION: {
    color: "#f9a825",
    badgeBg: "#fffbe6",
    badgeText: "#856404",
    label: "주의",
  },
  RISK: RISK_STYLE,
  HIGH_RISK: HIGH_RISK_STYLE,
  DANGER: RISK_STYLE,
  HIGH_DANGER: HIGH_RISK_STYLE,
};

export default function RiskDonut({
  score,
  grade,
  label,
  riskFactorCount,
  size = 96,
}: RiskDonutProps) {
  /* 미지의 grade(예: 신규 백엔드 값) 가 들어와도 crash 하지 않도록 NORMAL 로 fallback */
  const config = GRADE_CONFIG[grade] ?? GRADE_CONFIG.NORMAL;
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - score / 100);
  const center = size / 2;

  return (
    <div className="flex flex-col items-center gap-2">
      {/* SVG 도넛 */}
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          role="img"
          aria-label={`${label} 위험도 ${score}%, ${config.label}`}
        >
          {/* 배경 링 */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#f0f0f0"
            strokeWidth={10}
          />
          {/* 진행 링 */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={config.color}
            strokeWidth={10}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform={`rotate(-90 ${center} ${center})`}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>

        {/* 중앙 텍스트 */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-lg font-black"
            style={{ color: config.color, lineHeight: 1 }}
          >
            {Math.round(Number(score))}%
          </span>
        </div>
      </div>

      {/* 등급 배지 */}
      <span
        className="px-2 py-0.5 rounded-full text-xs font-bold"
        style={{
          backgroundColor: config.badgeBg,
          color: config.badgeText,
        }}
      >
        {config.label}
      </span>

      {/* 질병명 */}
      <p className="text-sm font-semibold text-text-primary text-center">
        {label}
      </p>

      {/* 위험인자 수 */}
      <p className="text-xs text-text-tertiary">
        위험인자 {riskFactorCount}개
      </p>
    </div>
  );
}
