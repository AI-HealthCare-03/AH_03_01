"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { usePredictionsList } from "@/hooks/queries/usePredictionsList";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import { useRiskRecommendation } from "@/hooks/queries/useRiskRecommendation";
import { useMe } from "@/hooks/queries/useMe";
import RiskSemiGauge from "@/components/health/RiskSemiGauge";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type { RiskGrade, DiseaseType, ChallengeCategory } from "@/types/api";
import type { ContributingFactor, PredictionDetail } from "@/types/health";

/* ── 상수 ──────────────────────────── */

const DISEASE_LABELS: Record<DiseaseType, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
};

const DISEASE_TABS: { id: DiseaseType; label: string }[] = [
  { id: "HYPERTENSION", label: "고혈압" },
  { id: "DIABETES", label: "당뇨" },
  { id: "CARDIOVASCULAR", label: "심혈관" },
];

/* 질환 아이콘 (이미지 없이 이모지 사용) */
const DISEASE_ICONS: Record<DiseaseType, string> = {
  HYPERTENSION: "🩸",
  DIABETES: "🍬",
  CARDIOVASCULAR: "❤️",
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
  CARDIOVASCULAR: "심혈관계 질환 위험도를 나타냅니다.",
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

const FACTOR_TOOLTIP: Record<string, string> = {
  bp_cat:
    "혈압을 4단계로 구분한 지표입니다. 정상 → 주의혈압 → 고혈압1기 → 고혈압2기 순으로 위험도가 높아집니다.",
  bmi_age_index:
    "나이가 많을수록 BMI의 건강 위험이 커진다는 점을 반영한 지표입니다.",
  metabolic_age:
    "혈당·비만·운동·수면 상태를 종합해 계산한 몸의 실제 나이입니다. 실제 나이보다 높을수록 건강 관리가 필요합니다.",
  GLYCEMIC_BURDEN_PROXY:
    "혈당 관련 15개 지표를 종합한 혈당 부담 점수입니다. 높을수록 당뇨 위험이 큽니다.",
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

/* ── 헬퍼: 기여인자 표시 라벨 ──── */

function factorDisplayText(f: ContributingFactor): string {
  if (f.description) {
    return f.description
      .replace(/\s*(위험\s*(증가|감소)[↑↓]?)?\s*$/, "")
      .trim();
  }
  return f.name_kor ?? "기여 요인";
}

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
}

function DiseaseCard({
  disease,
  score,
  grade,
  riskLevelLabel,
}: DiseaseCardProps) {
  const accent = DISEASE_ACCENT[disease];

  return (
    <div
      className="bg-white rounded-[16px] shadow-[0_2px_8px_rgba(0,0,0,0.07)] overflow-hidden flex flex-col items-center pt-0 pb-4"
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
      <div className="mt-2">
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
    </div>
  );
}

/* ========================================================
   3. 마스코트 말풍선
   ======================================================== */

function MascotBanner({ userName }: { userName: string | null }) {
  const name = userName ?? "회원";

  return (
    <div className="bg-[#fffde7] rounded-[16px] p-4 flex items-center gap-4 shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
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
      <div className="bg-white rounded-[12px] px-4 py-3 shadow-sm flex-1 relative">
        {/* 말풍선 꼬리 */}
        <div
          className="absolute left-[-8px] top-1/2 -translate-y-1/2 w-0 h-0"
          style={{
            borderTop: "6px solid transparent",
            borderBottom: "6px solid transparent",
            borderRight: "8px solid white",
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
    <div className="bg-[#fffde7] rounded-[16px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
      <p className="text-sm font-black text-text-primary mb-3">
        한눈에 보는 맞춤 요약
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        {chips.map((chip) => (
          <div
            key={chip.icon}
            className="bg-white rounded-[12px] p-3 shadow-[0_1px_3px_rgba(0,0,0,0.06)]"
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
  factors: ContributingFactor[];
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

  const maxWeight = Math.max(...factors.map((f) => Math.abs(f.weight)), 1);

  return (
    <div className="space-y-3.5">
      {factors.map((f, idx) => {
        const pct = Math.min(
          Math.round((Math.abs(f.weight) / maxWeight) * 100),
          100,
        );
        const displayText = factorDisplayText(f);
        const direction =
          f.direction ?? (f.weight > 0 ? "위험 증가↑" : "위험 감소↓");
        const isRisk = direction.includes("증가") || f.weight > 0;
        const tooltip = FACTOR_TOOLTIP[f.factor];

        /* 막대 색: 위험 증가→빨강→주황(상대 강도), 감소→파랑 */
        const barColor = isRisk
          ? pct > 70
            ? "bg-red-500"
            : pct > 40
              ? "bg-orange-400"
              : "bg-yellow-400"
          : "bg-blue-400";
        const directionColor = isRisk ? "text-red-600" : "text-blue-500";

        return (
          <div key={`${f.factor}-${idx}`}>
            <div className="flex justify-between mb-1.5">
              <span className="text-sm text-text-primary font-medium flex items-center gap-1">
                {displayText}
                {tooltip && (
                  <span className="relative group inline-flex">
                    <span className="text-[10px] text-text-tertiary border border-border rounded-full w-4 h-4 flex items-center justify-center cursor-help leading-none select-none">
                      ?
                    </span>
                    <span className="absolute left-0 bottom-5 z-10 hidden group-hover:block w-60 bg-gray-800 text-white text-[11px] rounded-[8px] px-3 py-2 shadow-lg leading-relaxed pointer-events-none">
                      {tooltip}
                    </span>
                  </span>
                )}
              </span>
              <span className={`text-xs font-bold ${directionColor}`}>
                {pct}%
              </span>
            </div>
            <div className="h-2.5 bg-surface rounded-full overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full transition-all duration-500`}
                style={{ width: `${pct}%` }}
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${displayText} 기여도 ${pct}%`}
              />
            </div>
            <p className={`text-[11px] mt-0.5 font-medium ${directionColor}`}>
              {direction}
            </p>
          </div>
        );
      })}

      <p className="text-[11px] text-text-tertiary border-t border-border pt-2 mt-2">
        (i) 막대 길이는 전체 인자 중 상대적 기여 비중입니다. 높을수록 위험도에
        큰 영향을 줍니다.
      </p>
    </div>
  );
}

/* ── 기여도 카드 (탭 포함) ──── */

interface ContributingCardProps {
  activeDisease: DiseaseType;
  onChangeDisease: (d: DiseaseType) => void;
  selectedDetail?: PredictionDetail;
  selectedPredId?: number;
}

function ContributingCard({
  activeDisease,
  onChangeDisease,
  selectedDetail,
  selectedPredId,
}: ContributingCardProps) {
  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.07)] flex-1 min-w-0">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-text-primary">위험 인자 기여도</h3>
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

      {/* 권고사항 CTA */}
      {selectedPredId && (
        <Link
          href={`/predictions/${selectedPredId}/recommendations`}
          className="mt-5 w-full flex items-center justify-center gap-2 py-3 bg-brand text-brand-black font-bold rounded-[12px] text-sm hover:bg-brand-hover transition-colors"
        >
          자세히 보기 →
        </Link>
      )}
    </div>
  );
}

/* ========================================================
   6. AI 맞춤 제안 섹션
   ======================================================== */

function AiSuggestions({ predictionId }: { predictionId: number | undefined }) {
  const { data: recData, isLoading: recLoading } =
    useRiskRecommendation(predictionId);
  const { data: challengeData, isLoading: challengeLoading } =
    useChallengeRecommendations(predictionId, 3);

  const recommendations = recData?.recommendations ?? [];
  const challenges = challengeData?.items ?? [];

  const exerciseRec = recommendations.find((r) => r.category === "EXERCISE");
  const dietRec = recommendations.find((r) => r.category === "DIET");
  const generalRecs = recommendations
    .filter((r) => r.category !== "EXERCISE" && r.category !== "DIET")
    .slice(0, 3);
  const displayRecs =
    generalRecs.length > 0 ? generalRecs : recommendations.slice(0, 3);

  const dietItems = dietRec
    ? [dietRec.content]
    : [
        "채소·통곡물 위주 식단을 권장합니다.",
        "나트륨 섭취를 줄여보세요.",
        "규칙적인 식사 시간을 유지하세요.",
      ];

  if (!predictionId) return null;

  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.07)] space-y-5">
      <div className="flex items-center gap-2">
        <span className="text-lg" aria-hidden="true">
          ✨
        </span>
        <h3 className="font-bold text-text-primary">AI 맞춤 제안</h3>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {/* 권고사항 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span aria-hidden="true">🛡️</span> 권고사항
          </p>
          {recLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-8 bg-surface rounded-[8px]" />
              ))}
            </div>
          ) : displayRecs.length > 0 ? (
            <>
              <ul className="space-y-2">
                {displayRecs.map((rec, i) => (
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
                    <span>{rec.content}</span>
                  </li>
                ))}
              </ul>
              <Link
                href={`/predictions/${predictionId}/recommendations`}
                className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
              >
                자세히 보기 →
              </Link>
            </>
          ) : (
            <Link
              href={`/predictions/${predictionId}/recommendations`}
              className="block text-xs text-brand-black font-semibold underline"
            >
              자세히 보기 →
            </Link>
          )}
        </div>

        {/* 추천 챌린지 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span aria-hidden="true">🚩</span> 추천 챌린지
          </p>
          {challengeLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-8 bg-surface rounded-[8px]" />
              ))}
            </div>
          ) : challenges.length > 0 ? (
            <>
              <ul className="space-y-2">
                {challenges.map((item, idx) => (
                  <li
                    key={item.template_id ?? item.challenge_id ?? idx}
                    className="flex items-center gap-2 p-2 bg-[#fffde7] rounded-[8px]"
                  >
                    <span className="text-base shrink-0" aria-hidden="true">
                      {CATEGORY_CONFIG[item.category as ChallengeCategory]
                        ?.emoji ?? "💪"}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-text-primary truncate">
                        {item.title && item.title !== item.category
                          ? item.title
                          : (CATEGORY_CONFIG[item.category as ChallengeCategory]
                              ?.label ?? item.category)}
                      </p>
                      <p className="text-[10px] text-brand-black font-bold">
                        +{item.reward_points ?? 200}P
                      </p>
                    </div>
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
            <p className="text-xs text-text-tertiary">
              추천 챌린지가 없습니다.
            </p>
          )}
        </div>

        {/* 식단 추천 — DIET 권고사항 기반, 없으면 일반 가이드라인 플레이스홀더 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span aria-hidden="true">🍽️</span> 식단 추천
          </p>
          {exerciseRec && (
            <div className="p-2 bg-surface rounded-[8px] mb-2">
              <p className="text-[11px] text-text-secondary">
                {exerciseRec.content}
              </p>
            </div>
          )}
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

  return (
    <div className="bg-[#fffde7] rounded-[14px] border border-[#ffe082] p-4 flex items-start gap-3">
      <span className="text-lg shrink-0 mt-0.5" aria-hidden="true">
        🛡️
      </span>
      <p className="text-[11px] text-text-secondary leading-relaxed">
        {content}
      </p>
    </div>
  );
}

/* ========================================================
   메인 컴포넌트
   ======================================================== */

export default function RiskTab() {
  const [activeDisease, setActiveDisease] =
    useState<DiseaseType>("HYPERTENSION");

  const { data: meData } = useMe();
  const { data: latestPredictions, isLoading: l1 } = useLatestPredictions();
  const { data: detailPredictions, isLoading: l2 } = usePredictionsList({
    latest: true,
  });

  const isLoading = l1 || l2;

  const latestItems = latestPredictions?.items ?? [];
  const detailItems =
    (detailPredictions as { items?: PredictionDetail[] } | null)?.items ?? [];

  /* 도넛 데이터 */
  const diseaseData: {
    disease: DiseaseType;
    score: number;
    grade: RiskGrade;
    riskLevelLabel?: string | null;
    predId?: number;
  }[] = DISEASE_TABS.map(({ id }) => {
    const lite = latestItems.find((p) => p.disease_type === id);
    const detail = detailItems.find((p) => p.disease_type === id);
    return {
      disease: id,
      score: Math.round(Number(lite?.risk_score ?? detail?.risk_score ?? 0)),
      grade:
        riskLevelToGrade(detail?.risk_level) ?? lite?.risk_grade ?? "NORMAL",
      riskLevelLabel: detail?.risk_level_label ?? null,
      predId: lite?.id ?? detail?.id,
    };
  });

  /* 선택된 질환 */
  const selectedDetail = detailItems.find(
    (p) => p.disease_type === activeDisease,
  );
  const selectedLite = latestItems.find(
    (p) => p.disease_type === activeDisease,
  );
  const selectedPredId = selectedLite?.id;

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

  /* 가장 큰 영향 요인 */
  const highestDetail = detailItems.find(
    (p) => p.disease_type === highestDiseaseData?.disease,
  );
  const topFactor = highestDetail?.contributing_factors?.[0]
    ? factorDisplayText(highestDetail.contributing_factors[0])
    : null;

  /* AI 제안용 — 최고 위험 질환 예측 ID */
  const highestPredId = highestDiseaseData?.predId;

  /* 최근 분석일 */
  const latestDate = latestItems[0]?.created_at
    ? new Date(latestItems[0].created_at).toLocaleDateString("ko-KR")
    : null;

  /* disclaimer — 상세 예측 중 첫 번째 것 사용 */
  const disclaimer = detailItems[0]?.disclaimer;

  const userName = meData?.nickname ?? meData?.name ?? null;

  /* ── 로딩 ── */
  if (isLoading) {
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

  /* ── 데이터 없음 ── */
  if (latestItems.length === 0) {
    return (
      <div className="text-center py-16 space-y-3">
        <p className="text-5xl" aria-hidden="true">
          🔍
        </p>
        <p className="font-bold text-text-primary text-lg">
          위험도 분석이 없습니다
        </p>
        <p className="text-sm text-text-secondary">
          건강 기록을 입력하면 맞춤 위험도 분석을 받을 수 있어요.
        </p>
        <Link
          href="/health-records/new"
          className="inline-flex items-center gap-1 mt-2 px-5 py-2.5 bg-brand text-brand-black font-semibold rounded-[12px] text-sm hover:bg-brand-hover transition-colors"
        >
          건강 기록 입력하기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* 1. 헤더 */}
      <HeaderSection userName={userName} latestDate={latestDate} />

      {/* 2. 질환 카드 3개 */}
      <div className="grid grid-cols-3 gap-3">
        {diseaseData.map((d) => (
          <DiseaseCard
            key={d.disease}
            disease={d.disease}
            score={d.score}
            grade={d.grade}
            riskLevelLabel={d.riskLevelLabel}
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

      {/* 5. 기여도 + (데스크탑) AI 제안 사이드 */}
      <div className="flex gap-4">
        <ContributingCard
          activeDisease={activeDisease}
          onChangeDisease={setActiveDisease}
          selectedDetail={selectedDetail}
          selectedPredId={selectedPredId}
        />
      </div>

      {/* 6. AI 맞춤 제안 */}
      <AiSuggestions predictionId={highestPredId} />

      {/* 7. Disclaimer 바 */}
      <DisclaimerBar text={disclaimer} />
    </div>
  );
}
