"use client";

import { useState } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { useLatestPredictions, LATEST_PREDICTIONS_KEY } from "@/hooks/queries/useLatestPredictions";
import { RAG_RISK_RECOMMENDATION_KEY } from "@/hooks/queries/useRagRiskRecommendation";
import { streamRagRiskRecommendation } from "@/lib/api/health";
import { compareAndPushRiskNotifications } from "@/lib/riskNotification";
import { useMe } from "@/hooks/queries/useMe";
import { useProfileCompleteness } from "@/hooks/queries/useProfileCompleteness";
import RiskSemiGauge from "@/components/health/RiskSemiGauge";
import { renderMarkdown } from "@/components/community/MarkdownEditor";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type { RiskGrade, DiseaseType, ChallengeCategory } from "@/types/api";
import type { RagRiskRecommendationResponse, RecommendedChallengeItem } from "@/types/health";
import { MISSING_FIELD_LABEL } from "@/lib/healthFields";

/* ── 상수 ──────────────────────────── */

// CARDIOVASCULAR enum 은 실제 이상지질혈증(DI2_dg) 모델 — 표시 라벨은 "이상지질혈증"으로 통일.
const DISEASE_LABELS: Record<DiseaseType, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "이상지질혈증",
};

const DISEASE_TABS: { id: DiseaseType; label: string }[] = [
  { id: "DIABETES", label: "당뇨" },
  { id: "HYPERTENSION", label: "고혈압" },
  { id: "CARDIOVASCULAR", label: "이상지질혈증" },
];

/* 질환 아이콘 (이미지 없이 이모지 사용) */
const DISEASE_ICONS: Record<DiseaseType, string> = {
  HYPERTENSION: "🩸",
  DIABETES: "🍬",
  CARDIOVASCULAR: "🧈",
};

/* 질환 서브컬러 — 카드 상단 강조선 */
const DISEASE_ACCENT: Record<DiseaseType, string> = {
  HYPERTENSION: "#e53935",
  DIABETES: "#43a047",
  CARDIOVASCULAR: "#e53935",
};

/* 질환 카드 설명 */
const DISEASE_DESC: Record<DiseaseType, string> = {
  HYPERTENSION: "혈압 관리가 필요한 수준을 나타냅니다.",
  DIABETES: "혈당 조절 위험도를 나타냅니다.",
  CARDIOVASCULAR: "이상지질혈증(콜레스테롤) 위험도를 나타냅니다.",
};

/* ── RiskLevel 매핑 ─────────────────── */

function riskLevelToGrade(level?: string): RiskGrade {
  switch (level) {
    case "NORMAL":
      return "NORMAL";
    case "CAUTION":
      return "CAUTION";
    case "RISK":
      return "DANGER";
    case "HIGH_RISK":
      return "HIGH_DANGER";
    default:
      return "NORMAL";
  }
}

/* ── 등급 라벨/색 ─────────────────── */

const GRADE_LABEL: Record<RiskGrade, string> = {
  NORMAL: "정상",
  CAUTION: "주의",
  RISK: "위험",
  DANGER: "위험",
  HIGH_RISK: "고위험",
  HIGH_DANGER: "고위험",
};

/* ── 파생변수 툴팁 설명 ──────────────── */

export const FACTOR_TOOLTIP: Record<string, string> = {
  bp_cat:
    "혈압을 4단계로 구분한 지표입니다. 정상 → 주의혈압 → 고혈압1기 → 고혈압2기 순으로 위험도가 높아집니다.",
  bmi_age_index:
    "나이가 많을수록 BMI의 건강 위험이 커진다는 점을 반영한 지표입니다.",
  metabolic_age:
    "혈당·비만·운동·수면 상태를 종합해 계산한 몸의 실제 나이입니다. 실제 나이보다 높을수록 건강 관리가 필요합니다.",
  GLYCEMIC_BURDEN_PROXY:
    "공복혈당·당화혈색소 추정치·혈당 상호작용(나이·비만·나트륨) 등 혈당 관련 15개 지표를 종합한 혈당 부담 점수입니다. 높을수록 당뇨 위험이 큽니다.",
  lipid_hidden_risk_proxy:
    "혈액검사 없이 생활습관(체형·음주·운동·호르몬)으로 추정한 숨은 지질 위험 점수입니다.",
  body_metabolic_score:
    "허리-키 비율·BMI·나이를 종합한 대사 건강 점수입니다. 높을수록 관리가 필요합니다.",
  fpg_risk_continuous:
    "공복혈당이 90mg/dL을 초과할수록 높아지는 위험 점수입니다.",
  WHtR: "허리둘레를 키로 나눈 값입니다. 0.5 이상이면 복부비만 위험 구간입니다.",
  WHtR_risk:
    "허리-키 비율을 기준으로 복부비만 위험을 0~1 점수로 나타낸 지표입니다.",
  prob_tg_cat_0: "AI가 예측한 '중성지방이 정상(<150mg/dL)일 가능성'입니다.",
  prob_tg_cat_1: "AI가 예측한 '중성지방이 경계(150~199mg/dL)일 가능성'입니다.",
  prob_tg_cat_2: "AI가 예측한 '중성지방이 높음(≥200mg/dL)일 가능성'입니다.",
  prob_hdl_cat_0:
    "AI가 예측한 'HDL이 낮을 가능성(남성 40 미만/여성 50 미만)'입니다.",
  prob_hdl_cat_1: "AI가 예측한 'HDL이 정상일 가능성'입니다.",
  prob_hdl_cat_2: "AI가 예측한 'HDL이 높음(≥60mg/dL)일 가능성'입니다.",
  prob_chol_cat_0:
    "AI가 예측한 '총콜레스테롤이 정상(<200mg/dL)일 가능성'입니다.",
  prob_chol_cat_1:
    "AI가 예측한 '총콜레스테롤이 경계(200~239mg/dL)일 가능성'입니다.",
  prob_chol_cat_2:
    "AI가 예측한 '총콜레스테롤이 높음(≥240mg/dL)일 가능성'입니다.",
  prob_ldl_cat_0: "AI가 예측한 'LDL이 최적(<100mg/dL)일 가능성'입니다.",
  prob_ldl_cat_1: "AI가 예측한 'LDL이 정상(100~129mg/dL)일 가능성'입니다.",
  prob_ldl_cat_2: "AI가 예측한 'LDL이 경계(130~159mg/dL)일 가능성'입니다.",
  prob_ldl_cat_3: "AI가 예측한 'LDL이 높음(160~189mg/dL)일 가능성'입니다.",
  prob_ldl_cat_4: "AI가 예측한 'LDL이 매우높음(≥190mg/dL)일 가능성'입니다.",
  TG_proxy_mgdl: "혈액검사 없이 체형·생활습관으로 추정한 중성지방 수치입니다.",
  HDL_proxy_mgdl: "혈액검사 없이 체형·운동·음주·나이로 추정한 HDL 수치입니다.",
  LDL_proxy: "총콜레스테롤·HDL·중성지방 추정값으로 계산한 LDL 수치입니다.",
  TC_residual_risk:
    "폐경·비만·가족력 등을 반영한 총콜레스테롤 추가 위험 점수입니다.",
  HDL_LOW_RISK_PROXY:
    "음주·복부비만·운동 부족으로 HDL이 낮아질 위험을 나타낸 지표입니다.",
  HDL_male_risk:
    "남성 전용 — 흡연·복부비만·운동 부족·음주로 인한 HDL 저하 위험입니다.",
  TG_male_risk:
    "남성 전용 — 음주·복부비만·혈당·BMI·나이를 종합한 중성지방 위험입니다.",
  TG_female_risk:
    "여성 전용 — 폐경·비만·혈당·나이를 종합한 중성지방 위험입니다.",
  HbA1c_proxy_home:
    "혈당 데이터로 추정한 당화혈색소 수치입니다. 실제 검사 결과와 다를 수 있습니다.",
  HbA1c_proxy_home_v2:
    "당화혈색소 추정 개선 버전입니다. 혈당부담 지수와 공복혈당을 함께 반영합니다.",
  glucose_age_interaction:
    "혈당이 높고 나이가 많을수록 함께 위험이 커지는 패턴을 반영한 지표입니다.",
  glucose_adiposity_interaction:
    "혈당이 높고 비만할수록 함께 위험이 커지는 패턴을 반영한 지표입니다.",
  glucose_sodium_interaction:
    "혈당이 높고 나트륨을 많이 섭취할수록 위험이 커지는 패턴을 반영한 지표입니다.",
  age_male_peak:
    "50대 초반 남성에서 심혈관 위험이 높아지는 연령 패턴을 반영한 지표입니다.",
  age_whtr_inter:
    "나이와 복부비만이 동시에 높을 때 위험이 커지는 패턴을 반영한 지표입니다.",
  SLEEP_AVG:
    "주중 5일과 주말 2일 수면시간을 가중 평균한 일평균 수면시간입니다.",
  SLEEP_WEEKDAY: "월~금 평균 수면시간입니다.",
  SLEEP_WEEKEND: "토·일 평균 수면시간입니다.",
  SLEEP_IMBALANCE:
    "주중과 주말 수면시간의 차이입니다. 클수록 수면 패턴이 불규칙합니다.",
  water_ml_per_kg: "체중 1kg당 하루 물 섭취량입니다.",
  tg_proxy_kde_pct:
    "같은 나이대와 비교했을 때 중성지방 수준이 어느 위치인지 나타냅니다.",
  hdl_proxy_kde_pct:
    "같은 나이대와 비교했을 때 HDL 수준이 어느 위치인지 나타냅니다.",
  ldl_proxy_kde_pct:
    "같은 나이대와 비교했을 때 LDL 수준이 어느 위치인지 나타냅니다.",
  tc_proxy_kde_pct:
    "같은 나이대와 비교했을 때 총콜레스테롤 수준이 어느 위치인지 나타냅니다.",
  gbp_kde_pct:
    "같은 나이대와 비교했을 때 혈당 부담이 어느 위치인지 나타냅니다.",
  meta_age_kde_pct:
    "같은 나이대와 비교했을 때 기능적 연령이 어느 위치인지 나타냅니다.",
  wt_bmi_idx_pct:
    "같은 나이대와 비교했을 때 체중-BMI 수준이 어느 위치인지 나타냅니다.",
  whtr_kde_pct_v2:
    "같은 나이대와 비교했을 때 허리-키 비율이 어느 위치인지 나타냅니다.",
};

/* ========================================================
   1. 헤더 섹션
   ======================================================== */

interface HeaderSectionProps {
  userName: string | null;
  latestDate: string | null;
}

function HeaderSection({ userName, latestDate }: HeaderSectionProps) {
  const displayName = userName ?? "회원";

  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        {/* 좌: 타이틀 */}
        <div>
          <h1 className="text-xl font-black text-text-primary leading-snug">
            <span className="text-[#d4a500]">{displayName}</span>님 맞춤
            <br className="sm:hidden" /> 위험도 리포트
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            입력하신 건강 데이터를 기반으로 AI가 분석한 결과예요.
          </p>
        </div>

        {/* 우: 날짜 + 입력 버튼 */}
        <div className="flex flex-col items-start sm:items-end gap-2 shrink-0">
          {latestDate && (
            <p className="text-xs text-text-tertiary">
              최근 분석일{" "}
              <span className="font-semibold text-text-secondary">
                {latestDate}
              </span>
            </p>
          )}
          <Link
            href="/health-records/new"
            className="inline-flex items-center gap-1 px-4 py-2 bg-brand text-brand-black text-sm font-bold rounded-[10px] hover:bg-brand-hover transition-colors"
          >
            건강 기록 입력하기 →
          </Link>
        </div>
      </div>
    </div>
  );
}

/* ========================================================
   2. 질환 카드 3개 (반원 게이지)
   ======================================================== */

interface DiseaseCardProps {
  disease: DiseaseType;
  score: number;
  grade: RiskGrade;
  riskLevelLabel?: string | null;
  /** true이면 이전 예측 이력 오버레이를 표시 */
  stale?: boolean;
  latestDate?: string | null;
  onPredict?: () => void;
  isPredicting?: boolean;
}

function DiseaseCard({
  disease,
  score,
  grade,
  riskLevelLabel,
  stale,
  latestDate,
  onPredict,
  isPredicting,
}: DiseaseCardProps) {
  const accent = DISEASE_ACCENT[disease];

  return (
    <div
      className="relative bg-white rounded-[16px] shadow-[0_2px_8px_rgba(0,0,0,0.07)] overflow-hidden flex flex-col items-center pt-0 pb-4"
      style={{ borderTop: `3px solid ${accent}` }}
    >
      {/* 질환명 + 아이콘 */}
      <div className="flex items-center gap-1.5 mt-4 mb-1">
        <span className="text-lg" aria-hidden="true">
          {DISEASE_ICONS[disease]}
        </span>
        <p className="text-sm font-bold text-text-primary">
          {DISEASE_LABELS[disease]}
        </p>
      </div>

      {/* 반원 게이지 */}
      <div className={stale ? "mt-2 blur-[2px]" : "mt-2"}>
        <RiskSemiGauge
          score={score}
          grade={grade}
          riskLevelLabel={riskLevelLabel}
          size={130}
        />
      </div>

      {/* 설명 */}
      <p className="mt-2 text-[11px] text-text-tertiary text-center px-3 leading-snug">
        {DISEASE_DESC[disease]}
      </p>

      {/* 이전 예측 이력 오버레이 */}
      {stale && onPredict && (
        <StaleResultOverlay
          latestDate={latestDate ?? null}
          onPredict={onPredict}
          isPredicting={isPredicting ?? false}
        />
      )}
    </div>
  );
}

/* ========================================================
   3. 마스코트 말풍선
   ======================================================== */

function MascotBanner({ userName }: { userName: string | null }) {
  const name = userName ?? "회원";

  return (
    <div className="bg-brand-light rounded-[16px] p-4 flex items-center gap-4 shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
      {/* 마스코트 이미지 */}
      <div className="shrink-0">
        <Image
          src="/images/mascot.png"
          alt="케어로그 마스코트"
          width={60}
          height={60}
          className="object-contain"
          onError={(e) => {
            /* 이미지 로드 실패 시 이모지로 폴백 */
            const target = e.currentTarget as HTMLImageElement;
            target.style.display = "none";
          }}
        />
      </div>
      {/* 말풍선 */}
      <div className="summary-chip bg-surface rounded-[12px] px-4 py-3 shadow-sm flex-1 relative">
        {/* 말풍선 꼬리 — 색은 className(border-r-white)으로 분리해 다크모드에서
            말풍선 배경(bg-surface)과 같은 색으로 바뀌도록 함(globals.css) */}
        <div
          className="absolute left-[-8px] top-1/2 -translate-y-1/2 w-0 h-0 border-r-white"
          style={{
            borderTop: "6px solid transparent",
            borderBottom: "6px solid transparent",
            borderRightWidth: "8px",
            borderRightStyle: "solid",
          }}
          aria-hidden="true"
        />
        <p className="text-sm font-semibold text-text-primary">
          {name}님에게 맞는 실천 포인트만 골라드렸어요!
        </p>
        <p className="text-xs text-text-tertiary mt-0.5">
          아래 내용을 꾸준히 실천하면 위험도를 낮출 수 있어요.
        </p>
      </div>
    </div>
  );
}

/* ========================================================
   4. 한눈에 보는 맞춤 요약 띠
   ======================================================== */

interface SummaryStripProps {
  highestDiseaseLabel: string;
  highestGrade: RiskGrade;
  topFactor: string | null;
  challengeGoal: string | null;
}

function SummaryStrip({
  highestDiseaseLabel,
  highestGrade,
  topFactor,
  challengeGoal,
}: SummaryStripProps) {
  const chips = [
    {
      icon: "🎯",
      keyword: highestDiseaseLabel || "—",
      desc: `${GRADE_LABEL[highestGrade]} 등급 — 우선 관리 필요`,
    },
    {
      icon: "🧂",
      keyword: topFactor || "데이터 입력 필요",
      desc: topFactor ? "가장 큰 영향 요인" : "건강 기록 입력 시 분석 가능",
    },
    {
      icon: "🚶",
      keyword: challengeGoal || "챌린지 참여하기",
      desc: "이번 주 추천 목표",
    },
    {
      icon: "🌙",
      keyword: "추가 데이터 입력",
      desc: "허리둘레·수면 등 입력 시 정확도 향상",
    },
  ];

  return (
    <div className="bg-brand-light rounded-[16px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
      <p className="text-sm font-black text-text-primary mb-3">
        한눈에 보는 맞춤 요약
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        {chips.map((chip) => (
          <div
            key={chip.icon}
            className="summary-chip bg-surface rounded-[12px] p-3 shadow-[0_1px_3px_rgba(0,0,0,0.06)]"
          >
            <p className="text-base mb-1" aria-hidden="true">
              {chip.icon}
            </p>
            <p className="text-xs font-bold text-text-primary leading-snug">
              {chip.keyword}
            </p>
            <p className="text-[11px] text-text-tertiary mt-0.5 leading-snug">
              {chip.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ========================================================
   5. 위험 인자 기여도 섹션
   ======================================================== */

interface ContributingBarsProps {
  factors: { factor: string; weight: number; description?: string; name_kor?: string; direction?: string }[];
}

function ContributingBars({ factors }: ContributingBarsProps) {
  if (factors.length === 0) {
    return (
      <div className="py-6 text-center space-y-2">
        <p className="text-sm text-text-tertiary">
          분석된 위험 인자가 없습니다.
        </p>
        <Link
          href="/health-records/new"
          className="text-sm font-semibold text-text-primary underline"
        >
          데이터 입력하기
        </Link>
      </div>
    );
  }

  // 기여도(%)는 "전체 인자 중 상대적 비중" — 절댓값 합으로 정규화해 합이 100%가 되게 한다.
  // (이전 max 정규화는 1순위 인자가 항상 100%로 표시돼 오해를 줬다.)
  const totalWeight = factors.reduce((sum, f) => sum + Math.abs(f.weight), 0) || 1;

  return (
    <div className="space-y-3">
      {factors.map((f) => {
        const pct = Math.round((Math.abs(f.weight) / totalWeight) * 100);
        const isRisk = f.weight > 0;
        // 위험도 결과가 정상인 사용자: 백엔드가 '정상 범위/주의 요인' 전용 방향을 보냄.
        const isNormalCtx = f.direction === "정상 범위" || f.direction === "주의 요인";
        // 라벨: name_kor(ML) 우선, 없으면 변수명.
        const label = f.name_kor ?? f.factor;
        // 중립 방향 문구 — 값(잦은/적은 등)을 단정하지 않고 기여 '방향'만 표현(사실 오류 방지).
        // 정상 예측 사용자는 '위험 증가/감소' 대신 정상 맥락 문구로 안내(혼란 방지).
        const neutralDesc = isNormalCtx
          ? f.direction === "정상 범위"
            ? "정상 범위라 위험을 낮게 유지하고 있어요"
            : "정상이지만 관심이 필요한 요인이에요"
          : isRisk
            ? "위험도를 높이는 방향으로 작용했어요"
            : "위험도를 낮추는 방향으로 작용했어요";
        // 파생변수 산출 방법 설명 — 있으면 ⓘ hover 툴팁으로 노출.
        const tooltip = FACTOR_TOOLTIP[f.factor];

        /* 막대 색: 위험 증가→빨강→주황(비중 강도), 감소→파랑
           contrib-bar-* 마커 클래스는 다크모드 전용 밝기 보정(globals.css)을
           다른 컴포넌트의 동일한 bg-red-500 등과 분리해서 적용하기 위함. */
        const barColor = isRisk
          ? pct >= 30
            ? "bg-red-500 contrib-bar-high"
            : pct >= 15
              ? "bg-orange-400 contrib-bar-mid"
              : "bg-yellow-400 contrib-bar-low"
          : "bg-blue-400 contrib-bar-down";

        return (
          <div key={f.factor}>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-text-primary font-medium inline-flex items-center gap-1">
                {label}
                {tooltip && (
                  <span
                    aria-label={tooltip}
                    role="tooltip"
                    tabIndex={0}
                    className="relative group/tip inline-flex items-center justify-center w-4 h-4 rounded-full bg-surface text-[10px] font-bold text-text-tertiary cursor-help select-none"
                  >
                    ?
                    <span
                      role="presentation"
                      className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-50 hidden group-hover/tip:block group-focus/tip:block w-56 max-w-[min(14rem,calc(100vw-2rem))] rounded-[8px] bg-gray-800 px-3 py-2 text-[11px] leading-snug text-white whitespace-normal break-keep shadow-lg"
                    >
                      {tooltip}
                      <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                    </span>
                  </span>
                )}
              </span>
              <span className="text-xs font-bold text-text-secondary">기여도 {pct}%</span>
            </div>
            <div className="h-2.5 bg-surface rounded-full overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full transition-all duration-500`}
                style={{ width: `${pct}%` }}
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${label} 기여도 ${pct}%`}
              />
            </div>
            <p className="text-xs text-text-tertiary mt-0.5">{neutralDesc}</p>
          </div>
        );
      })}

      <p className="text-[11px] text-text-tertiary border-t border-border pt-2 mt-2">
        (i) 기여도(%)는 전체 인자 중 상대적 기여 비중입니다. 높을수록 위험도에
        큰 영향을 줍니다. 항목 옆 ? 에 마우스를 올리면 산출 방법을 볼 수 있어요.
      </p>
    </div>
  );
}

/* ========================================================
   예측 실행 전 카드 오버레이 (이전 예측 이력임을 명시)
   ======================================================== */

interface StaleResultOverlayProps {
  latestDate: string | null;
  onPredict: () => void;
  isPredicting: boolean;
}

function StaleResultOverlay({ latestDate, onPredict, isPredicting }: StaleResultOverlayProps) {
  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-[16px] bg-white/80 backdrop-blur-[2px] px-3 text-center">
      <p className="text-[11px] font-semibold text-text-secondary leading-snug">
        {latestDate ? `마지막 예측: ${latestDate}` : "이전 예측 결과"}
      </p>
      <p className="text-[10px] text-text-tertiary leading-snug">
        최신 데이터로 다시 예측하세요
      </p>
      <button
        type="button"
        onClick={onPredict}
        disabled={isPredicting}
        className="mt-1 px-3 py-1.5 bg-brand-black text-white text-[11px] font-bold rounded-[8px] hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPredicting ? "분석 중..." : "예측 실행 →"}
      </button>
    </div>
  );
}

/* ── 기여도 카드 (탭 포함) ──── */

interface SelectedDetail {
  id: number;
  disease_type: DiseaseType;
  risk_score: number;
  risk_level: "NORMAL" | "CAUTION" | "RISK" | "HIGH_RISK";
  risk_grade: RiskGrade;
  risk_level_label?: string | null;
  contributing_factors: { factor: string; weight: number; description?: string; name_kor?: string; direction?: string }[];
  created_at: string;
}

interface ContributingCardProps {
  activeDisease: DiseaseType;
  onChangeDisease: (d: DiseaseType) => void;
  selectedDetail?: SelectedDetail;
}

function ContributingCard({
  activeDisease,
  onChangeDisease,
  selectedDetail,
}: ContributingCardProps) {
  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.07)] flex-1 min-w-0">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-text-primary">위험도 예측 기여도</h3>
      </div>

      {/* 질환 탭 */}
      <div className="flex gap-1.5 mb-5">
        {DISEASE_TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => onChangeDisease(id)}
            className={[
              "flex-1 py-2 text-sm font-semibold rounded-[10px] transition-colors border",
              activeDisease === id
                ? "bg-brand text-brand-black border-brand"
                : "text-text-secondary border-border hover:bg-surface",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 선택 질환 위험 수준 배지 */}
      {selectedDetail?.risk_level_label && (
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs text-text-tertiary">위험 수준</span>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#fffde7] text-[#856404] border border-[#ffe082]">
            {selectedDetail.risk_level_label}
          </span>
        </div>
      )}

      {/* 기여 인자 바 */}
      <ContributingBars factors={selectedDetail?.contributing_factors ?? []} />
    </div>
  );
}

/* ========================================================
   6. AI 맞춤 제안 섹션
   ======================================================== */

interface AiSuggestionsProps {
  ragResult: RagRiskRecommendationResponse | null;
}

/* 난이도 뱃지 라벨 */
const DIFFICULTY_LABEL: Record<string, string> = {
  LEVEL_1: "입문",
  LEVEL_2: "초급",
  LEVEL_3: "중급",
  LEVEL_4: "고급",
};

/* priority 뱃지 */
const PRIORITY_BADGE: Record<string, { label: string; className: string }> = {
  TOP: { label: "강력 추천", className: "bg-[#fff3cd] text-[#856404] border border-[#ffe082]" },
  RECOMMENDED: { label: "추천", className: "bg-[#e8f5e9] text-[#2e7d32] border border-[#a5d6a7]" },
  OPTIONAL: { label: "선택", className: "bg-surface text-text-tertiary border border-border" },
};

interface RecommendedChallengeCardProps {
  item: RecommendedChallengeItem;
}

function RecommendedChallengeCard({ item }: RecommendedChallengeCardProps) {
  const categoryConfig = CATEGORY_CONFIG[item.category as ChallengeCategory];
  const difficultyLabel = DIFFICULTY_LABEL[item.difficulty] ?? item.difficulty;
  const priorityBadge = item.priority ? PRIORITY_BADGE[item.priority] : null;

  return (
    <Link
      href="/challenges"
      className="flex items-start gap-3 p-3 bg-[#fffde7] rounded-[10px] hover:bg-[#fff9c4] transition-colors group"
      aria-label={`${item.title} 챌린지 보기`}
    >
      {/* 카테고리 이모지 */}
      <span className="text-xl shrink-0 mt-0.5" aria-hidden="true">
        {categoryConfig?.emoji ?? "💪"}
      </span>

      <div className="min-w-0 flex-1">
        {/* 제목 + priority 뱃지 */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <p className="text-xs font-bold text-text-primary leading-snug group-hover:underline">
            {item.title}
          </p>
          {priorityBadge && (
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${priorityBadge.className}`}>
              {priorityBadge.label}
            </span>
          )}
        </div>

        {/* 카테고리 + 난이도 뱃지 */}
        <div className="flex items-center gap-1.5 mt-1">
          <span className="px-1.5 py-0.5 bg-white rounded-full text-[10px] text-text-secondary border border-border">
            {categoryConfig?.label ?? item.category}
          </span>
          <span className="px-1.5 py-0.5 bg-white rounded-full text-[10px] text-text-secondary border border-border">
            {difficultyLabel}
          </span>
        </div>

        {/* reason 한 줄 */}
        {item.reason && (
          <p className="text-[10px] text-text-tertiary mt-1 leading-snug">
            {item.reason}
          </p>
        )}
      </div>
    </Link>
  );
}

function AiSuggestions({ ragResult }: AiSuggestionsProps) {
  // 권고 칩: recommended_tips (최대 3개 표시)
  const tips = ragResult?.recommended_tips?.slice(0, 3) ?? [];
  // 식단 칩: recommended_diet
  const dietItems = ragResult?.recommended_diet ?? [];
  // RAG 응답의 추천 챌린지
  const ragChallenges = ragResult?.recommended_challenges ?? [];

  if (!ragResult) return null;

  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.07)] space-y-5">
      <div className="flex items-center gap-2">
        <span className="text-lg" aria-hidden="true">
          ✨
        </span>
        <h3 className="font-bold text-text-primary">AI 맞춤 제안</h3>
      </div>

      {/* AI 권고 요약 — LLM 답변을 마크다운으로 렌더(볼드·줄바꿈·불릿). bg-surface 로 다크모드 가독성 확보. */}
      {ragResult.answer && (
        <div className="bg-surface rounded-[12px] p-4">
          <p className="text-xs font-semibold text-text-tertiary mb-1">AI 분석 요약</p>
          <div
            className="text-sm text-text-secondary leading-relaxed [&_strong]:font-semibold [&_strong]:text-text-primary [&_li]:my-0.5"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(ragResult.answer) }}
          />
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        {/* 권고사항 */}
        {tips.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-bold text-text-primary flex items-center gap-1">
              <span aria-hidden="true">🛡️</span> 권고사항
            </p>
            <ul className="space-y-2">
              {tips.map((tip, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs text-text-secondary"
                >
                  <span
                    className="text-status-success mt-0.5 shrink-0"
                    aria-hidden="true"
                  >
                    ✓
                  </span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 추천 챌린지 — RAG 응답 기반 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span aria-hidden="true">🚩</span> 추천 챌린지
          </p>
          {ragChallenges.length > 0 ? (
            <>
              <ul className="space-y-2">
                {ragChallenges.map((item) => (
                  <li key={item.template_id}>
                    <RecommendedChallengeCard item={item} />
                  </li>
                ))}
              </ul>
              <Link
                href="/challenges"
                className="inline-flex items-center gap-1 mt-1 px-3 py-1.5 bg-brand text-brand-black text-xs font-bold rounded-[8px] hover:bg-brand-hover transition-colors"
              >
                챌린지 참여하기 →
              </Link>
            </>
          ) : (
            <div className="space-y-1.5">
              <p className="text-xs text-text-tertiary">
                챌린지 추천은 예측 결과와 연동됩니다.
              </p>
              <Link
                href="/challenges"
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-surface text-text-secondary text-xs font-semibold rounded-[8px] hover:bg-brand hover:text-brand-black transition-colors"
              >
                전체 챌린지 보기 →
              </Link>
            </div>
          )}
        </div>

        {/* 식단 추천 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span aria-hidden="true">🍽️</span> 식단 추천
          </p>
          {dietItems.length > 0 ? (
            <ul className="space-y-2">
              {dietItems.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs text-text-secondary"
                >
                  <span
                    className="text-brand-black mt-0.5 shrink-0"
                    aria-hidden="true"
                  >
                    •
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-tertiary">
              식단 제안을 불러올 수 없습니다.
            </p>
          )}
        </div>
      </div>

      <p className="text-[10px] text-text-tertiary border-t border-border pt-3">
        본 권고사항은 입력하신 건강 데이터를 바탕으로 제공되는 일반적인 건강
        정보로, 의료적 진단이나 처방을 대체하지 않습니다. 정확한 진단과 치료는
        반드시 의료 전문가에게 문의하세요.
      </p>
    </div>
  );
}

/* ========================================================
   7. Disclaimer 바
   ======================================================== */

function DisclaimerBar({ text }: { text?: string }) {
  const content =
    text ??
    "본 위험도 결과는 입력하신 데이터를 기반으로 AI가 산출한 참고 정보입니다. 의학적 진단이나 처방을 대체하지 않으며, 정확한 진단·치료는 반드시 의료 전문가에게 문의하세요. 출처: KSH 2022 / KDA 2023 / KSoLA 2022 / KSSO 2022";
  const sourceIdx = content.indexOf("출처:");
  const mainText = sourceIdx === -1 ? content : content.slice(0, sourceIdx).trim();
  const sourceText = sourceIdx === -1 ? null : content.slice(sourceIdx);

  return (
    <div className="bg-surface rounded-[14px] p-4 flex items-start gap-3">
      <span className="text-lg shrink-0 mt-0.5" aria-hidden="true">
        🛡️
      </span>
      <p className="text-xs text-text-tertiary leading-relaxed">
        {mainText}
        {sourceText && (
          <>
            <br />
            {sourceText}
          </>
        )}
      </p>
    </div>
  );
}

/* ========================================================
   메인 컴포넌트
   ======================================================== */

/* ========================================================
   컴플리트니스 게이트 섹션
   ======================================================== */

interface CompletenessGateProps {
  percent: number;
  filled: number;
  total: number;
  missingFields: string[];
  complete: boolean;
  isPredicting: boolean;
  stageLabel?: string | null;
  onPredict: () => void;
}

function CompletenessGate({
  percent,
  filled,
  total,
  missingFields,
  complete,
  isPredicting,
  stageLabel,
  onPredict,
}: CompletenessGateProps) {
  /* SVG 링 파라미터 */
  const SIZE = 72;
  const STROKE = 7;
  const R = (SIZE - STROKE) / 2;
  const CIRCUMFERENCE = 2 * Math.PI * R;
  const offset = CIRCUMFERENCE - (percent / 100) * CIRCUMFERENCE;

  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
      <div className="flex items-start gap-4">
        {/* 완성도 Ring */}
        <div className="shrink-0 flex flex-col items-center gap-1">
          <svg width={SIZE} height={SIZE} aria-hidden="true">
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={R}
              fill="none"
              stroke="#f0f0f0"
              strokeWidth={STROKE}
            />
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={R}
              fill="none"
              stroke={complete ? "#22c55e" : "#d4a500"}
              strokeWidth={STROKE}
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
              style={{ transition: "stroke-dashoffset 0.6s ease" }}
            />
            <text
              x={SIZE / 2}
              y={SIZE / 2 + 5}
              textAnchor="middle"
              fontSize="14"
              fontWeight="700"
              fill={complete ? "#22c55e" : "#333"}
            >
              {percent}%
            </text>
          </svg>
          <p className="text-[10px] text-text-tertiary">{filled}/{total}</p>
        </div>

        {/* 텍스트 + 버튼 */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-text-primary mb-0.5">
            {complete ? "모든 데이터가 입력되었어요" : "건강 데이터 입력 현황"}
          </p>
          {!complete ? (
            <>
              <p className="text-xs text-text-secondary mb-2">
                건강데이터를 전부 입력해주셔야 예측 결과를 확인하실 수 있습니다.
                아직 {missingFields.length}개 항목이 남았습니다.
              </p>
              {missingFields.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {missingFields.slice(0, 6).map((f) => (
                    <span
                      key={f}
                      className="px-2 py-0.5 bg-[#fff3cd] text-[#856404] text-[11px] rounded-full border border-[#ffe082]"
                    >
                      {MISSING_FIELD_LABEL[f] ?? f}
                    </span>
                  ))}
                  {missingFields.length > 6 && (
                    <span className="px-2 py-0.5 bg-surface text-text-tertiary text-[11px] rounded-full">
                      +{missingFields.length - 6}개
                    </span>
                  )}
                </div>
              )}
              <Link
                href="/health-records/complete"
                className="inline-flex items-center gap-1 px-4 py-2 bg-brand text-brand-black text-sm font-bold rounded-[10px] hover:bg-brand-hover transition-colors"
              >
                누락 항목 채우기 →
              </Link>
            </>
          ) : (
            <>
              <p className="text-xs text-text-secondary mb-3">
                모든 항목이 입력되어 위험도 예측을 실행할 수 있어요.
              </p>
              <button
                type="button"
                onClick={onPredict}
                disabled={isPredicting}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-brand-black text-white text-sm font-bold rounded-[10px] hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPredicting ? (
                  <>
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
                    {stageLabel || "분석 중..."}
                  </>
                ) : (
                  "위험도 예측 실행 →"
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ========================================================
   메인 컴포넌트
   ======================================================== */

export default function RiskTab() {
  const [activeDisease, setActiveDisease] =
    useState<DiseaseType>("HYPERTENSION");
  const [predictError, setPredictError] = useState<string | null>(null);
  const [mlUnavailable, setMlUnavailable] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [stageLabel, setStageLabel] = useState<string | null>(null);

  const { data: meData } = useMe();
  const { data: latestPredictions, isLoading: latestLoading } = useLatestPredictions();
  const { data: completeness, isLoading: completenessLoading } = useProfileCompleteness();
  const queryClient = useQueryClient();

  // 예측 실행 이후 캐시된 RAG 결과 읽기 (useMutation onSuccess 에서 setQueryData 로 저장됨)
  const ragResult = useQuery<RagRiskRecommendationResponse>({
    queryKey: RAG_RISK_RECOMMENDATION_KEY,
    enabled: false, // 직접 fetch 하지 않음 — mutation onSuccess 에서만 채워짐
  }).data ?? null;

  const isLoading = latestLoading || completenessLoading;

  /* ── 예측 실행 핸들러 (SSE 스트리밍) ── */
  const handlePredict = async () => {
    setPredictError(null);
    setMlUnavailable(false);
    setStageLabel(null);
    setIsStreaming(true);
    try {
      await streamRagRiskRecommendation({
        // 그래프 진행 단계를 버튼 라벨로 노출 (건강정보 확인 → 위험도 예측 → 자료 검색 → 권고 작성 → 검토).
        onStage: ({ label }) => setStageLabel(label),
        onDone: (result) => {
          // 비스트림과 동일: 결과를 캐시에 저장 후 데이터부족/fallback/성공 분기.
          queryClient.setQueryData(RAG_RISK_RECOMMENDATION_KEY, result);
          if (!result.has_required_data) {
            setPredictError("건강데이터를 전부 입력해주셔야 예측 결과를 확인하실 수 있습니다.");
          } else if (result.is_fallback) {
            setMlUnavailable(true);
          } else {
            // 성공 — latestPredictions 도 갱신해 latestDate 반영
            void queryClient.invalidateQueries({ queryKey: LATEST_PREDICTIONS_KEY });

            // 위험도 변화 알림
            compareAndPushRiskNotifications(result.predictions ?? []);
          }
        },
        onError: (message) => {
          // DB 장애·throttle 등은 error 이벤트로 전달됨(스트림은 HTTP status 대신 메시지).
          setPredictError(message || "예측 실행 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
        },
      });
    } finally {
      // 스트림이 done/error 이벤트 없이 비정상 종료돼도 버튼 로딩이 풀리도록 항상 정리.
      setStageLabel(null);
      setIsStreaming(false);
    }
  };

  const latestItems = latestPredictions?.items ?? [];

  /* 도넛 데이터 — RAG 응답 있으면 우선 사용, 없으면 latestPredictions fallback */
  const ragPredictions = ragResult?.predictions ?? [];
  const diseaseData: {
    disease: DiseaseType;
    score: number;
    grade: RiskGrade;
    riskLevelLabel?: string | null;
  }[] = DISEASE_TABS.map(({ id }) => {
    const ragItem = ragPredictions.find((p) => p.disease_type === id);
    const liteItem = latestItems.find((p) => p.disease_type === id);
    return {
      disease: id,
      score: Math.round(Number(ragItem?.risk_score ?? liteItem?.risk_score ?? 0)),
      grade: ragItem ? riskLevelToGrade(ragItem.risk_level) : (liteItem?.risk_grade ?? "NORMAL"),
      // 게이지 라벨은 모델 클래스(risk_level→grade) 기준으로 표시한다. score 백분위 5단계
      // 라벨(risk_level_label)은 실제 판정과 어긋나 부정확해 사용하지 않는다.
      riskLevelLabel: null,
    };
  });

  /* 선택된 질환 기여 인자 — RAG 응답 우선 */
  const selectedRagPrediction = ragPredictions.find(
    (p) => p.disease_type === activeDisease,
  );
  // ContributingCard 가 요구하는 PredictionDetail 형태와 호환되는 객체 구성
  const selectedDetail = selectedRagPrediction
    ? {
        id: 0,
        disease_type: selectedRagPrediction.disease_type,
        risk_score: selectedRagPrediction.risk_score,
        risk_level: selectedRagPrediction.risk_level,
        risk_grade: riskLevelToGrade(selectedRagPrediction.risk_level),
        contributing_factors: selectedRagPrediction.contributing_factors,
        created_at: "",
      }
    : undefined;

  /* 종합: 가장 높은 위험 질환 */
  const gradeOrder: RiskGrade[] = [
    "HIGH_DANGER",
    "HIGH_RISK",
    "DANGER",
    "RISK",
    "CAUTION",
    "NORMAL",
  ];
  const highestGrade =
    diseaseData
      .map((d) => d.grade)
      .sort((a, b) => gradeOrder.indexOf(a) - gradeOrder.indexOf(b))[0] ??
    "NORMAL";

  const highestDiseaseData = diseaseData
    .filter((d) => d.grade === highestGrade)
    .sort((a, b) => b.score - a.score)[0];

  const highestDiseaseLabel = diseaseData
    .filter((d) => d.grade === highestGrade)
    .map((d) => DISEASE_LABELS[d.disease])
    .join(", ");

  /* 가장 큰 영향 요인 — RAG 응답 우선 */
  const highestRagPrediction = ragPredictions.find(
    (p) => p.disease_type === highestDiseaseData?.disease,
  );
  const topFactor = highestRagPrediction?.contributing_factors?.[0]
    ? (() => {
        const f = highestRagPrediction.contributing_factors[0];
        return (
          f.name_kor ??
          (f.description
            ? f.description.replace(/\s*(위험\s*(증가|감소)[↑↓]?)?\s*$/, "").trim()
            : f.factor)
        );
      })()
    : null;

  /* 최근 분석일 — latestPredictions 기반 유지 */
  const latestDate = latestItems[0]?.created_at
    ? new Date(latestItems[0].created_at).toLocaleDateString("ko-KR")
    : null;

  /* disclaimer — RAG 응답 우선, 없으면 DisclaimerBar 기본값 */
  const disclaimer = ragResult?.disclaimer;

  const userName = meData?.nickname ?? meData?.name ?? null;

  const isPredicting = isStreaming;

  /* ── 로딩 ── */
  if (isLoading || completenessLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-28 bg-surface rounded-[16px]" />
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-52 bg-surface rounded-[16px]" />
          ))}
        </div>
        <div className="h-16 bg-surface rounded-[16px]" />
        <div className="h-20 bg-surface rounded-[16px]" />
        <div className="h-64 bg-surface rounded-[16px]" />
      </div>
    );
  }

  /* ── 상태 1: 프로필 미완성 — 건강데이터 부족(stale 예측 카드는 절대 표시하지 않음) ── */
  if (completeness?.complete === false) {
    return (
      <div className="space-y-5">
        <CompletenessGate
          percent={completeness?.percent ?? 0}
          filled={completeness?.filled ?? 0}
          total={completeness?.total ?? 0}
          missingFields={completeness?.missing_fields ?? []}
          complete={false}
          isPredicting={isPredicting}
          stageLabel={stageLabel}
          onPredict={handlePredict}
        />
        {predictError && (
          <p className="text-sm text-red-600 bg-red-50 rounded-[12px] p-3">{predictError}</p>
        )}
        <div className="text-center py-8 space-y-2">
          <p className="text-5xl" aria-hidden="true">📝</p>
          <p className="font-bold text-text-primary text-lg">
            건강데이터를 전부 입력해주셔야 예측 결과를 확인하실 수 있습니다
          </p>
          <p className="text-sm text-text-secondary">
            누락된 항목을 모두 입력하면 맞춤 위험도 분석 결과를 받을 수 있어요.
          </p>
        </div>
      </div>
    );
  }

  /* ── 상태 2: 모델 장애 (예측 호출이 503 ML_UNAVAILABLE 또는 is_fallback=true) ── */
  if (mlUnavailable) {
    return (
      <div className="space-y-5">
        <CompletenessGate
          percent={completeness?.percent ?? 100}
          filled={completeness?.filled ?? 0}
          total={completeness?.total ?? 0}
          missingFields={completeness?.missing_fields ?? []}
          complete
          isPredicting={isPredicting}
          stageLabel={stageLabel}
          onPredict={handlePredict}
        />
        <div className="text-center py-8 space-y-2">
          <p className="text-5xl" aria-hidden="true">⚙️</p>
          <p className="font-bold text-text-primary text-lg">위험도 예측 준비 중</p>
          <p className="text-sm text-text-secondary">잠시 후 다시 시도해 주세요.</p>
        </div>
      </div>
    );
  }

  /* ── 상태 3: 완성이지만 표시할 예측 결과 없음 (RAG 결과도 없고 기존 예측도 없음) ── */
  if (latestItems.length === 0 && ragPredictions.length === 0) {
    return (
      <div className="space-y-5">
        <CompletenessGate
          percent={completeness?.percent ?? 100}
          filled={completeness?.filled ?? 0}
          total={completeness?.total ?? 0}
          missingFields={completeness?.missing_fields ?? []}
          complete
          isPredicting={isPredicting}
          stageLabel={stageLabel}
          onPredict={handlePredict}
        />
        {predictError && (
          <p className="text-sm text-red-600 bg-red-50 rounded-[12px] p-3">{predictError}</p>
        )}
        <div className="text-center py-8 space-y-2">
          <p className="text-5xl" aria-hidden="true">🔍</p>
          <p className="font-bold text-text-primary text-lg">예측 결과가 확인이 되지 않고 있습니다</p>
          <p className="text-sm text-text-secondary">
            위험도 예측을 실행하면 맞춤 분석 결과를 받을 수 있어요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* 1. 헤더 */}
      <HeaderSection userName={userName} latestDate={latestDate} />

      {/* 완성도 + 예측 버튼 게이트 */}
      <CompletenessGate
        percent={completeness?.percent ?? 100}
        filled={completeness?.filled ?? 0}
        total={completeness?.total ?? 0}
        missingFields={completeness?.missing_fields ?? []}
        complete={completeness?.complete ?? false}
        isPredicting={isPredicting}
        stageLabel={stageLabel}
        onPredict={handlePredict}
      />
      {predictError && (
        <p className="text-sm text-red-600 bg-red-50 rounded-[12px] p-3">{predictError}</p>
      )}

      {/* 2. 질환 카드 3개 */}
      {/* ragResult === null: 이번 세션에서 예측 미실행 → 이전 이력 카드는 stale 오버레이 */}
      {ragResult === null && latestItems.length > 0 && (
        <div className="flex items-center gap-2 px-1 pb-1">
          <span className="text-xs text-[#856404] bg-[#fff3cd] border border-[#ffe082] rounded-full px-2.5 py-0.5">
            마지막 예측: {latestDate ?? "이전 결과"} — 최신 데이터로 다시 예측해 보세요
          </span>
        </div>
      )}
      <div className="grid grid-cols-3 gap-3">
        {diseaseData.map((d) => (
          <DiseaseCard
            key={d.disease}
            disease={d.disease}
            score={d.score}
            grade={d.grade}
            riskLevelLabel={d.riskLevelLabel}
            stale={ragResult === null && latestItems.length > 0}
            latestDate={latestDate}
            onPredict={handlePredict}
            isPredicting={isPredicting}
          />
        ))}
      </div>

      {/* 3. 마스코트 말풍선 */}
      <MascotBanner userName={userName} />

      {/* 4. 맞춤 요약 띠 */}
      <SummaryStrip
        highestDiseaseLabel={highestDiseaseLabel}
        highestGrade={highestGrade}
        topFactor={topFactor}
        challengeGoal={null}
      />

      {/* 5. 기여도 카드 */}
      <div className="flex gap-4">
        <ContributingCard
          activeDisease={activeDisease}
          onChangeDisease={setActiveDisease}
          selectedDetail={selectedDetail}
        />
      </div>

      {/* 6. AI 맞춤 제안 */}
      <AiSuggestions ragResult={ragResult} />

      {/* 7. Disclaimer 바 */}
      <DisclaimerBar text={disclaimer} />
    </div>
  );
}
