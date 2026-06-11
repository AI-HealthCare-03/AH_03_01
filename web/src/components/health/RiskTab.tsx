"use client";

import { useState } from "react";
import Link from "next/link";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { usePredictionsList } from "@/hooks/queries/usePredictionsList";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import { useRiskRecommendation } from "@/hooks/queries/useRiskRecommendation";
import RiskDonut from "@/components/home/RiskDonut";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import type { RiskGrade, DiseaseType, ChallengeCategory } from "@/types/api";
import type { PredictionDetail } from "@/types/health";

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

/* ── RiskLevel 매핑 ─────────────────── */

function riskLevelToGrade(level?: string): RiskGrade {
  switch (level) {
    case "NORMAL": return "NORMAL";
    case "CAUTION": return "CAUTION";
    case "RISK": return "DANGER";
    case "HIGH_RISK": return "HIGH_DANGER";
    default: return "NORMAL";
  }
}

/* ── 파생변수 툴팁 설명 ──────────────── */

const FACTOR_TOOLTIP: Record<string, string> = {
  // 혈압
  bp_cat:                  "혈압을 4단계로 구분한 지표입니다. 정상 → 주의혈압 → 고혈압1기 → 고혈압2기 순으로 위험도가 높아집니다.",
  // 복합 지수
  bmi_age_index:           "나이가 많을수록 BMI의 건강 위험이 커진다는 점을 반영한 지표입니다.",
  metabolic_age:           "혈당·비만·운동·수면 상태를 종합해 계산한 몸의 실제 나이입니다. 실제 나이보다 높을수록 건강 관리가 필요합니다.",
  GLYCEMIC_BURDEN_PROXY:   "혈당 관련 15개 지표를 종합한 혈당 부담 점수입니다. 높을수록 당뇨 위험이 큽니다.",
  lipid_hidden_risk_proxy: "혈액검사 없이 생활습관(체형·음주·운동·호르몬)으로 추정한 숨은 지질 위험 점수입니다.",
  body_metabolic_score:    "허리-키 비율·BMI·나이를 종합한 대사 건강 점수입니다. 높을수록 관리가 필요합니다.",
  // 혈당
  fpg_risk_continuous:     "공복혈당이 90mg/dL을 초과할수록 높아지는 위험 점수입니다.",
  // 체형
  WHtR:                    "허리둘레를 키로 나눈 값입니다. 0.5 이상이면 복부비만 위험 구간입니다.",
  WHtR_risk:               "허리-키 비율을 기준으로 복부비만 위험을 0~1 점수로 나타낸 지표입니다.",
  // 지질 메타 피처 (이상지질혈증 예측 중간 단계)
  prob_tg_cat_0:           "AI가 예측한 '중성지방이 정상(<150mg/dL)일 가능성'입니다.",
  prob_tg_cat_1:           "AI가 예측한 '중성지방이 경계(150~199mg/dL)일 가능성'입니다.",
  prob_tg_cat_2:           "AI가 예측한 '중성지방이 높음(≥200mg/dL)일 가능성'입니다.",
  prob_hdl_cat_0:          "AI가 예측한 'HDL이 낮을 가능성(남성 40 미만/여성 50 미만)'입니다.",
  prob_hdl_cat_1:          "AI가 예측한 'HDL이 정상일 가능성'입니다.",
  prob_hdl_cat_2:          "AI가 예측한 'HDL이 높음(≥60mg/dL)일 가능성'입니다.",
  prob_chol_cat_0:         "AI가 예측한 '총콜레스테롤이 정상(<200mg/dL)일 가능성'입니다.",
  prob_chol_cat_1:         "AI가 예측한 '총콜레스테롤이 경계(200~239mg/dL)일 가능성'입니다.",
  prob_chol_cat_2:         "AI가 예측한 '총콜레스테롤이 높음(≥240mg/dL)일 가능성'입니다.",
  prob_ldl_cat_0:          "AI가 예측한 'LDL이 최적(<100mg/dL)일 가능성'입니다.",
  prob_ldl_cat_1:          "AI가 예측한 'LDL이 정상(100~129mg/dL)일 가능성'입니다.",
  prob_ldl_cat_2:          "AI가 예측한 'LDL이 경계(130~159mg/dL)일 가능성'입니다.",
  prob_ldl_cat_3:          "AI가 예측한 'LDL이 높음(160~189mg/dL)일 가능성'입니다.",
  prob_ldl_cat_4:          "AI가 예측한 'LDL이 매우높음(≥190mg/dL)일 가능성'입니다.",
  // 지질 추정치
  TG_proxy_mgdl:           "혈액검사 없이 체형·생활습관으로 추정한 중성지방 수치입니다.",
  HDL_proxy_mgdl:          "혈액검사 없이 체형·운동·음주·나이로 추정한 HDL 수치입니다.",
  LDL_proxy:               "총콜레스테롤·HDL·중성지방 추정값으로 계산한 LDL 수치입니다.",
  TC_residual_risk:        "폐경·비만·가족력 등을 반영한 총콜레스테롤 추가 위험 점수입니다.",
  HDL_LOW_RISK_PROXY:      "음주·복부비만·운동 부족으로 HDL이 낮아질 위험을 나타낸 지표입니다.",
  HDL_male_risk:           "남성 전용 — 흡연·복부비만·운동 부족·음주로 인한 HDL 저하 위험입니다.",
  TG_male_risk:            "남성 전용 — 음주·복부비만·혈당·BMI·나이를 종합한 중성지방 위험입니다.",
  TG_female_risk:          "여성 전용 — 폐경·비만·혈당·나이를 종합한 중성지방 위험입니다.",
  // 혈당 추정
  HbA1c_proxy_home:        "혈당 데이터로 추정한 당화혈색소 수치입니다. 실제 검사 결과와 다를 수 있습니다.",
  HbA1c_proxy_home_v2:     "당화혈색소 추정 개선 버전입니다. 혈당부담 지수와 공복혈당을 함께 반영합니다.",
  // 혈당 상호작용
  glucose_age_interaction: "혈당이 높고 나이가 많을수록 함께 위험이 커지는 패턴을 반영한 지표입니다.",
  glucose_adiposity_interaction: "혈당이 높고 비만할수록 함께 위험이 커지는 패턴을 반영한 지표입니다.",
  glucose_sodium_interaction:    "혈당이 높고 나트륨을 많이 섭취할수록 위험이 커지는 패턴을 반영한 지표입니다.",
  // 나이 관련
  age_male_peak:           "50대 초반 남성에서 심혈관 위험이 높아지는 연령 패턴을 반영한 지표입니다.",
  age_whtr_inter:          "나이와 복부비만이 동시에 높을 때 위험이 커지는 패턴을 반영한 지표입니다.",
  // 수면
  SLEEP_AVG:               "주중 5일과 주말 2일 수면시간을 가중 평균한 일평균 수면시간입니다.",
  SLEEP_WEEKDAY:           "월~금 평균 수면시간입니다 (취침 시각과 기상 시각으로 계산).",
  SLEEP_WEEKEND:           "토·일 평균 수면시간입니다 (취침 시각과 기상 시각으로 계산).",
  SLEEP_IMBALANCE:         "주중과 주말 수면시간의 차이입니다. 클수록 수면 패턴이 불규칙합니다.",
  // 수분
  water_ml_per_kg:         "체중 1kg당 하루 물 섭취량입니다. 수분 섭취가 충분한지 나타냅니다.",
  // KDE 백분위 (동일 연령대 비교)
  tg_proxy_kde_pct:        "같은 나이대와 비교했을 때 중성지방 수준이 어느 위치인지 나타냅니다.",
  hdl_proxy_kde_pct:       "같은 나이대와 비교했을 때 HDL 수준이 어느 위치인지 나타냅니다.",
  ldl_proxy_kde_pct:       "같은 나이대와 비교했을 때 LDL 수준이 어느 위치인지 나타냅니다.",
  tc_proxy_kde_pct:        "같은 나이대와 비교했을 때 총콜레스테롤 수준이 어느 위치인지 나타냅니다.",
  gbp_kde_pct:             "같은 나이대와 비교했을 때 혈당 부담이 어느 위치인지 나타냅니다.",
  meta_age_kde_pct:        "같은 나이대와 비교했을 때 기능적 연령이 어느 위치인지 나타냅니다.",
  wt_bmi_idx_pct:          "같은 나이대와 비교했을 때 체중-BMI 수준이 어느 위치인지 나타냅니다.",
  whtr_kde_pct_v2:         "같은 나이대와 비교했을 때 허리-키 비율이 어느 위치인지 나타냅니다.",
};

/* ── 기여 인자 바 ───────────────────── */

interface ContributingBarsProps {
  factors: { factor: string; weight: number; description?: string; name_kor?: string }[];
}

function ContributingBars({ factors }: ContributingBarsProps) {
  if (factors.length === 0) {
    return (
      <div className="py-6 text-center space-y-1">
        <p className="text-sm text-text-tertiary">분석된 위험 인자가 없습니다.</p>
        <Link href="/health-records/new" className="text-sm font-semibold text-text-primary underline">
          데이터 입력하기
        </Link>
      </div>
    );
  }

  const maxWeight = Math.max(...factors.map((f) => Math.abs(f.weight)), 1);

  return (
    <div className="space-y-3">
      {factors.map((f) => {
        const pct = Math.min(Math.round((Math.abs(f.weight) / maxWeight) * 100), 100);
        const isRisk = f.weight > 0;
        const barColor = isRisk ? "bg-status-danger" : "bg-blue-400";
        const friendlyDir = isRisk ? "위험도를 높이는 요인입니다" : "위험도를 낮추는 요인입니다";
        // name_kor 있으면(ML) 그대로 라벨 사용, 없으면(rule-based) description에서 방향 suffix 제거
        const label = f.name_kor
          ?? (f.description
            ? f.description.replace(/\s*(위험\s*(증가|감소)[↑↓]?)?\s*$/, "").trim()
            : f.factor);
        // ML 경로는 description이 user-friendly 문장, rule-based는 짧은 이름이므로 방향 텍스트로 보완
        const userDesc = f.name_kor
          ? (f.description ?? friendlyDir)
          : friendlyDir;

        return (
          <div key={f.factor}>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-text-primary font-medium">{label}</span>
              <span className="text-xs font-bold text-text-secondary">{pct}점</span>
            </div>
            <div className="h-2 bg-surface rounded-full overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full transition-all duration-500`}
                style={{ width: `${pct}%` }}
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${label} 기여도`}
              />
            </div>
            <p className="text-xs text-text-tertiary mt-0.5">{userDesc}</p>
          </div>
        );
      })}
    </div>
  );
}

/* ── 한눈에 보는 요약 카드 ─────────── */

interface SummaryCardsProps {
  highestDiseaseLabel: string;
  highestGrade: RiskGrade;
  topFactor: string | null;
  challengeGoal: string | null;
}

const GRADE_COLOR: Record<RiskGrade, string> = {
  NORMAL: "text-status-success",
  CAUTION: "text-status-warning",
  RISK: "text-status-danger",
  DANGER: "text-status-danger",
  HIGH_RISK: "text-status-danger",
  HIGH_DANGER: "text-status-danger",
};

const GRADE_LABEL: Record<RiskGrade, string> = {
  NORMAL: "정상", CAUTION: "주의", RISK: "위험",
  DANGER: "위험", HIGH_RISK: "고위험", HIGH_DANGER: "고위험",
};

function SummaryCards({ highestDiseaseLabel, highestGrade, topFactor, challengeGoal }: SummaryCardsProps) {
  const cards = [
    {
      icon: "🎯",
      title: "가장 우선 관리",
      value: highestDiseaseLabel || "—",
      sub: GRADE_LABEL[highestGrade],
      subColor: GRADE_COLOR[highestGrade],
    },
    {
      icon: "⚠️",
      title: "가장 큰 영향 요인",
      value: topFactor || "—",
      sub: topFactor ? "위험 기여 1위" : "데이터 입력 필요",
      subColor: "text-text-tertiary",
    },
    {
      icon: "🏃",
      title: "이번 주 추천 목표",
      value: challengeGoal || "챌린지 참여하기",
      sub: "건강 개선 시작",
      subColor: "text-text-tertiary",
    },
    {
      icon: "📊",
      title: "정확도 향상",
      value: "추가 데이터 입력",
      sub: "허리둘레·수면 등 입력 시 향상",
      subColor: "text-text-tertiary",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.title}
          className="bg-white rounded-[14px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.08)]"
        >
          <p className="text-xl mb-2">{card.icon}</p>
          <p className="text-[11px] text-text-tertiary font-medium mb-1">{card.title}</p>
          <p className="text-sm font-bold text-text-primary leading-snug">{card.value}</p>
          <p className={`text-[11px] mt-0.5 font-medium ${card.subColor}`}>{card.sub}</p>
        </div>
      ))}
    </div>
  );
}

/* ── AI 맞춤 제안 ───────────────────── */

function AiSuggestions({ predictionId }: { predictionId: number | undefined }) {
  const { data: recData, isLoading: recLoading } = useRiskRecommendation(predictionId);
  const { data: challengeData, isLoading: challengeLoading } = useChallengeRecommendations(predictionId, 3);

  const recommendations = recData?.recommendations ?? [];
  const challenges = challengeData?.items ?? [];

  /* 카테고리별 권고사항 분류 */
  const exerciseRec = recommendations.find((r) => r.category === "EXERCISE");
  const dietRec = recommendations.find((r) => r.category === "DIET");
  const generalRecs = recommendations.filter(
    (r) => r.category !== "EXERCISE" && r.category !== "DIET"
  ).slice(0, 3);
  const displayRecs = generalRecs.length > 0 ? generalRecs : recommendations.slice(0, 3);

  /* 식단 추천 — DIET 권고사항 or 기본 문구 */
  const dietItems = dietRec
    ? [dietRec.content]
    : ["채소·통곡물 위주 식단을 권장합니다.", "나트륨 섭취를 줄여보세요.", "규칙적인 식사 시간을 유지하세요."];

  if (!predictionId) return null;

  return (
    <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
      <div className="flex items-center gap-2">
        <span className="text-lg">✨</span>
        <h3 className="font-bold text-text-primary">AI 맞춤 제안</h3>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {/* 권고사항 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span>💡</span> 권고사항
          </p>
          {recLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-surface rounded-[8px]" />)}
            </div>
          ) : displayRecs.length > 0 ? (
            <ul className="space-y-2">
              {displayRecs.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                  <span className="text-status-success mt-0.5 shrink-0">✓</span>
                  <span>{rec.content}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Link
              href={`/predictions/${predictionId}/recommendations`}
              className="block text-xs text-brand-black font-semibold underline"
            >
              자세히 보기 →
            </Link>
          )}
          {displayRecs.length > 0 && (
            <Link
              href={`/predictions/${predictionId}/recommendations`}
              className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
            >
              자세히 보기 →
            </Link>
          )}
        </div>

        {/* 추천 챌린지 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span>🏆</span> 추천 챌린지
          </p>
          {challengeLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-surface rounded-[8px]" />)}
            </div>
          ) : challenges.length > 0 ? (
            <ul className="space-y-2">
              {challenges.map((item, idx) => (
                <li
                  key={item.template_id ?? item.challenge_id ?? idx}
                  className="flex items-center gap-2 p-2 bg-surface rounded-[8px]"
                >
                  <span className="text-base shrink-0">
                    {CATEGORY_CONFIG[item.category as ChallengeCategory]?.emoji ?? "💪"}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-text-primary truncate">
                      {item.title && item.title !== item.category
                        ? item.title
                        : (CATEGORY_CONFIG[item.category as ChallengeCategory]?.label ?? item.category)}
                    </p>
                    <p className="text-[10px] text-brand-black font-bold">+{item.reward_points ?? 200}P</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-tertiary">추천 챌린지가 없습니다.</p>
          )}
        </div>

        {/* 식단 추천 */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-text-primary flex items-center gap-1">
            <span>🥗</span> 식단 추천
          </p>
          {exerciseRec && (
            <div className="p-2 bg-surface rounded-[8px] mb-2">
              <p className="text-[11px] text-text-secondary">{exerciseRec.content}</p>
            </div>
          )}
          <ul className="space-y-2">
            {dietItems.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="text-brand-black mt-0.5 shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 면책 */}
      <p className="text-[10px] text-text-tertiary border-t border-border pt-3">
        본 권고사항은 입력하신 건강 데이터를 바탕으로 제공되는 일반적인 건강 정보로,
        의료적 진단이나 처방을 대체하지 않습니다. 정확한 진단과 치료는 반드시 의료 전문가에게 문의하세요.
      </p>
    </div>
  );
}

/* ── 맞춤 챌린지 추천 사이드 (데스크탑) ── */

function RecommendedChallengesSide({ predictionId }: { predictionId: number | undefined }) {
  const { data, isLoading } = useChallengeRecommendations(predictionId, 3);

  return (
    <div className="hidden md:block w-64 shrink-0">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <h3 className="font-bold text-sm text-text-primary mb-3">맞춤 챌린지 추천</h3>
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-surface rounded-[8px]" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {(data?.items ?? []).map((item, idx) => (
              <div
                key={item.template_id ?? item.challenge_id ?? item.id ?? idx}
                className="flex flex-col gap-0.5 p-3 bg-surface rounded-[10px]"
              >
                <div className="flex items-center gap-1 mb-0.5">
                  <span className="text-sm">
                    {CATEGORY_CONFIG[item.category as ChallengeCategory]?.emoji ?? "💪"}
                  </span>
                  <p className="text-xs font-semibold text-text-primary">
                    {item.title && item.title !== item.category
                      ? item.title
                      : (CATEGORY_CONFIG[item.category as ChallengeCategory]?.label ?? item.category)}
                  </p>
                </div>
                {item.reason && !item.reason.includes("위험도") && (
                  <p className="text-[11px] text-text-tertiary">{item.reason}</p>
                )}
                <p className="text-[11px] text-brand-black font-bold">
                  +{item.reward_points ?? 200}P
                </p>
              </div>
            ))}
            {(!data || data.items.length === 0) && (
              <p className="text-xs text-text-tertiary">추천 챌린지가 없습니다.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── 면책 ─────────────────────────── */

function Disclaimer() {
  return (
    <div className="rounded-[12px] bg-surface border border-border p-4 text-xs text-text-secondary space-y-1">
      <p className="font-semibold text-text-primary">안내 사항</p>
      <p>
        본 위험도 결과는 의학적 진단이 아닙니다. 정확한 진단·치료는 반드시 의료 전문가에게
        문의하세요.
      </p>
      <p className="text-text-tertiary mt-1">
        출처: KSH 2022 고혈압 진료지침 / KDA 2023 당뇨병 진료지침 /
        KSoLA 2022 이상지질혈증 / KSSO 2022 비만 진료지침
      </p>
    </div>
  );
}

/* ── 메인 컴포넌트 ─────────────────── */

export default function RiskTab() {
  const [activeDisease, setActiveDisease] = useState<DiseaseType>("HYPERTENSION");

  const { data: latestPredictions, isLoading: l1 } = useLatestPredictions();
  const { data: detailPredictions, isLoading: l2 } = usePredictionsList({ latest: true });

  const isLoading = l1 || l2;

  const latestItems = latestPredictions?.items ?? [];
  const detailItems = (detailPredictions as { items?: PredictionDetail[] } | null)?.items ?? [];

  /* 도넛 데이터 */
  const donutData: {
    disease: DiseaseType;
    score: number;
    grade: RiskGrade;
    factorCount: number;
    predId?: number;
  }[] = DISEASE_TABS.map(({ id }) => {
    const lite = latestItems.find((p) => p.disease_type === id);
    const detail = detailItems.find((p) => p.disease_type === id);
    return {
      disease: id,
      score: Math.round(Number(lite?.risk_score ?? detail?.risk_score ?? 0)),
      grade: riskLevelToGrade(detail?.risk_level) ?? (lite?.risk_grade ?? "NORMAL"),
      factorCount: detail?.contributing_factors?.length ?? 0,
      predId: lite?.id ?? detail?.id,
    };
  });

  /* 현재 선택된 disease 의 상세 */
  const selectedDetail = detailItems.find((p) => p.disease_type === activeDisease);
  const selectedLite = latestItems.find((p) => p.disease_type === activeDisease);
  const selectedPredId = selectedLite?.id;

  /* 종합 등급 헤드라인 — 가장 높은 위험 */
  const gradeOrder: RiskGrade[] = ["HIGH_RISK", "HIGH_DANGER", "RISK", "DANGER", "CAUTION", "NORMAL"];
  const highestGrade =
    donutData
      .map((d) => d.grade)
      .sort((a, b) => gradeOrder.indexOf(a) - gradeOrder.indexOf(b))[0] ?? "NORMAL";

  const highestDiseaseData = donutData
    .filter((d) => d.grade === highestGrade)
    .sort((a, b) => b.score - a.score)[0];

  const highestDiseaseLabel =
    donutData
      .filter((d) => d.grade === highestGrade)
      .map((d) => DISEASE_LABELS[d.disease])
      .join(", ");

  /* 가장 큰 영향 요인 — 최고 위험 질환의 top1 기여 인자 */
  const highestDetail = detailItems.find(
    (p) => p.disease_type === highestDiseaseData?.disease
  );
  const topFactor = highestDetail?.contributing_factors?.[0]
    ? (() => {
        const f = highestDetail.contributing_factors[0];
        return (
          f.name_kor ??
          (f.description
            ? f.description.replace(/\s*(위험\s*(증가|감소)[↑↓]?)?\s*$/, "").trim()
            : f.factor)
        );
      })()
    : null;

  /* AI 맞춤 제안용 — 최고 위험 질환 예측 ID */
  const highestPredId = highestDiseaseData?.predId;

  /* 추천 챌린지 첫 번째 — 요약 카드용 */
  const latestUpdated =
    latestItems[0]?.created_at
      ? new Date(latestItems[0].created_at).toLocaleDateString("ko-KR")
      : null;

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-32 bg-surface rounded-[16px]" />
        <div className="h-64 bg-surface rounded-[16px]" />
      </div>
    );
  }

  if (latestItems.length === 0) {
    return (
      <div className="text-center py-16 space-y-3">
        <p className="text-5xl">🔍</p>
        <p className="font-bold text-text-primary text-lg">위험도 분석이 없습니다</p>
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
      {/* 헤드라인 */}
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-text-tertiary">종합 등급</p>
            <p className="text-xl font-black text-text-primary mt-1">
              {highestDiseaseLabel}{" "}
              <span className="text-status-danger">{GRADE_LABEL[highestGrade]}</span>
            </p>
          </div>
          {latestUpdated && (
            <p className="text-xs text-text-tertiary">갱신: {latestUpdated}</p>
          )}
        </div>
      </div>

      {/* 3 도넛 */}
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <div className="flex justify-around">
          {donutData.map((d) => (
            <RiskDonut
              key={d.disease}
              score={d.score}
              grade={d.grade}
              label={DISEASE_LABELS[d.disease]}
              riskFactorCount={d.factorCount}
              size={96}
            />
          ))}
        </div>
      </div>

      {/* 한눈에 보는 요약 카드 */}
      <SummaryCards
        highestDiseaseLabel={highestDiseaseLabel}
        highestGrade={highestGrade}
        topFactor={topFactor}
        challengeGoal={null}
      />

      {/* 카테고리 탭 + 기여 인자 */}
      <div className="flex gap-4">
        <div className="flex-1 min-w-0 bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
          {/* 탭 */}
          <div className="flex gap-1 mb-5">
            {DISEASE_TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActiveDisease(id)}
                className={[
                  "flex-1 py-2 text-sm font-medium rounded-[8px] transition-colors border",
                  activeDisease === id
                    ? "bg-brand-black text-white border-brand-black"
                    : "text-text-secondary border-border hover:text-text-primary",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>

          {/* 기여 인자 */}
          <ContributingBars factors={selectedDetail?.contributing_factors ?? []} />

          {/* 권고사항 CTA */}
          {selectedPredId && (
            <Link
              href={`/predictions/${selectedPredId}/recommendations`}
              className="mt-5 w-full flex items-center justify-center gap-2 py-3 bg-brand text-brand-black font-semibold rounded-[12px] text-sm hover:bg-brand-hover transition-colors"
            >
              권고사항 보기 →
            </Link>
          )}
        </div>

        {/* 데스크탑 사이드: 맞춤 챌린지 */}
        <RecommendedChallengesSide predictionId={selectedPredId} />
      </div>

      {/* AI 맞춤 제안 */}
      <AiSuggestions predictionId={highestPredId} />

      {/* 면책 */}
      <Disclaimer />
    </div>
  );
}
