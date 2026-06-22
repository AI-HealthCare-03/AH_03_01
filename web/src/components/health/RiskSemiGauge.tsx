"use client";

/* =========================================
   반원 게이지 컴포넌트
   목업의 "반원 게이지" 무드를 SVG arc 로 구현.
   전체 원 도넛(RiskDonut) 과 별개로 RiskTab 전용.
   ========================================= */

import type { RiskGrade } from "@/types/api";

interface RiskSemiGaugeProps {
  /** 0~100 점수 */
  score: number;
  grade: RiskGrade;
  /** 등급 라벨 (5단계 한글: risk_level_label, 없으면 grade→내부 라벨 사용) */
  riskLevelLabel?: string | null;
  size?: number;
}

/* ── 등급별 스타일 ──── */

const RISK_STYLE = {
  arc: "#e53935",
  badge: "#ffeaea",
  badgeText: "#c62828",
  label: "위험",
} as const;
const HIGH_RISK_STYLE = {
  arc: "#b71c1c",
  badge: "#ffcdd2",
  badgeText: "#b71c1c",
  label: "고위험",
} as const;

const GRADE_STYLE: Record<
  RiskGrade,
  { arc: string; badge: string; badgeText: string; label: string }
> = {
  NORMAL: {
    arc: "#2e7d32",
    badge: "#e8f5e9",
    badgeText: "#2e7d32",
    label: "정상",
  },
  CAUTION: {
    arc: "#f9a825",
    badge: "#fffbe6",
    badgeText: "#856404",
    label: "주의",
  },
  RISK: RISK_STYLE,
  HIGH_RISK: HIGH_RISK_STYLE,
  DANGER: RISK_STYLE,
  HIGH_DANGER: HIGH_RISK_STYLE,
};

/**
 * 반원(180도) SVG 아크를 그린다.
 * score 0 → 왼쪽 끝, score 100 → 오른쪽 끝.
 */
function describeArc(
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number,
) {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(startDeg));
  const y1 = cy + r * Math.sin(toRad(startDeg));
  const x2 = cx + r * Math.cos(toRad(endDeg));
  const y2 = cy + r * Math.sin(toRad(endDeg));
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export default function RiskSemiGauge({
  score,
  grade,
  riskLevelLabel,
  size = 140,
}: RiskSemiGaugeProps) {
  const style = GRADE_STYLE[grade] ?? GRADE_STYLE.NORMAL;

  /* 반원: 180deg ~ 360deg (하단 반원 사용, 위를 향해 열린 아치) */
  const cx = size / 2;
  const cy = size * 0.62; /* 아크 중심을 아래쪽으로 배치 */
  const r = size * 0.38;

  /* 아크 진행도: -180deg(왼쪽) → 0deg(오른쪽) — 상단 반원 */
  const startAngle = 180;
  const endAngle = 180 + Math.min(score, 100) * 1.8; /* 180deg 범위 */

  const bgPath = describeArc(cx, cy, r, 180, 360);
  const arcPath = describeArc(cx, cy, r, startAngle, endAngle);

  const displayLabel = riskLevelLabel ?? style.label;
  const clampedScore = Math.round(Math.min(Math.max(score, 0), 100));

  return (
    <div
      className="flex flex-col items-center"
      role="img"
      aria-label={`위험도 ${clampedScore}%, ${displayLabel}`}
    >
      <div style={{ width: size, height: size * 0.72 }} className="relative">
        <svg
          width={size}
          height={size * 0.72}
          viewBox={`0 0 ${size} ${size * 0.72}`}
          overflow="visible"
        >
          {/* 배경 아크 */}
          <path
            d={bgPath}
            fill="none"
            stroke="#eeeeee"
            strokeWidth={size * 0.085}
            strokeLinecap="round"
          />
          {/* 진행 아크 */}
          <path
            d={arcPath}
            fill="none"
            stroke={style.arc}
            strokeWidth={size * 0.085}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.7s ease" }}
          />
        </svg>

        {/* 중앙 숫자 */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-end pb-1"
          aria-hidden="true"
        >
          <span
            className="font-black leading-none"
            style={{ color: style.arc, fontSize: size * 0.19 }}
          >
            {clampedScore}%
          </span>
        </div>
      </div>

      {/* 등급 배지 */}
      <span
        className="mt-1 px-3 py-0.5 rounded-full text-xs font-bold"
        style={{ background: style.badge, color: style.badgeText }}
      >
        {displayLabel}
      </span>
    </div>
  );
}
