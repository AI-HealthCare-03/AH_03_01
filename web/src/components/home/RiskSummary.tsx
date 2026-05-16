"use client";

/* =========================================
   질병 위험도 요약 섹션
   고혈압 / 당뇨 / 심혈관 도넛 3개
   ========================================= */

import Link from "next/link";
import { format } from "date-fns";
import RiskDonut from "./RiskDonut";
import type { PredictionItem, DiseaseType, RiskGrade } from "@/types/api";

interface RiskSummaryProps {
  predictions: PredictionItem[];
  isLoading: boolean;
  updatedAt?: string; /* ISO 날짜 문자열 */
}

const DISEASE_LABELS: Record<DiseaseType, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
};

const DISEASE_ORDER: DiseaseType[] = [
  "HYPERTENSION",
  "DIABETES",
  "CARDIOVASCULAR",
];

/* 예측 배열에서 질병별 최신 1개 추출 */
function getLatestByDisease(
  items: PredictionItem[]
): Map<DiseaseType, PredictionItem> {
  const map = new Map<DiseaseType, PredictionItem>();
  for (const item of items) {
    if (!map.has(item.disease_type)) {
      map.set(item.disease_type, item);
    }
  }
  return map;
}

export default function RiskSummary({
  predictions,
  isLoading,
  updatedAt,
}: RiskSummaryProps) {
  const latestMap = getLatestByDisease(predictions);
  const hasAny = latestMap.size > 0;
  const updatedLabel = updatedAt
    ? format(new Date(updatedAt), "yyyy.MM.dd")
    : "데이터 없음";

  return (
    <section aria-labelledby="risk-summary-heading">
      {/* 섹션 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2
            id="risk-summary-heading"
            className="text-base font-bold text-text-primary"
          >
            질병 위험도 요약
          </h2>
          {hasAny && (
            <p className="text-xs text-text-tertiary mt-0.5">
              최근 7일 데이터 기반 · {updatedLabel}
            </p>
          )}
        </div>
        <Link
          href="/predictions"
          className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
        >
          자세히 보기 →
        </Link>
      </div>

      {isLoading ? (
        /* 로딩 스켈레톤 */
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex flex-col items-center gap-2">
              <div className="w-24 h-24 rounded-full bg-surface animate-pulse" />
              <div className="h-3 w-14 bg-surface rounded animate-pulse" />
            </div>
          ))}
        </div>
      ) : hasAny ? (
        <>
          <div className="bg-white rounded-[16px] border border-border p-6 shadow-sm">
            <div className="grid grid-cols-3 gap-4">
              {DISEASE_ORDER.map((diseaseType) => {
                const pred = latestMap.get(diseaseType);
                if (!pred) {
                  return (
                    <div
                      key={diseaseType}
                      className="flex flex-col items-center gap-2 opacity-40"
                    >
                      <div className="w-24 h-24 rounded-full border-2 border-dashed border-border flex items-center justify-center text-xs text-text-tertiary text-center p-2">
                        데이터없음
                      </div>
                      <p className="text-sm font-semibold text-text-tertiary">
                        {DISEASE_LABELS[diseaseType]}
                      </p>
                    </div>
                  );
                }
                /* 백엔드 응답은 risk_level (NORMAL|CAUTION|RISK|HIGH_RISK) 와
                   contributing_factors 배열을 보낸다. 프론트 PredictionItem 타입에
                   정의된 risk_grade/risk_factors_count 는 없을 수 있으므로
                   안전하게 변환. */
                const p = pred as PredictionItem & {
                  risk_level?: string;
                  contributing_factors?: unknown[];
                };
                const grade =
                  (p.risk_grade ?? (p.risk_level as RiskGrade | undefined)) ?? "NORMAL";
                const score = Number(p.risk_score) || 0;
                const factorCount =
                  p.risk_factors_count ?? p.contributing_factors?.length ?? 0;
                return (
                  <RiskDonut
                    key={diseaseType}
                    score={score}
                    grade={grade as RiskGrade}
                    label={DISEASE_LABELS[diseaseType]}
                    riskFactorCount={factorCount}
                  />
                );
              })}
            </div>
          </div>

          {/* 면책 고지 */}
          <p className="mt-3 text-[11px] text-text-tertiary leading-relaxed">
            본 결과는 의학적 진단이 아닙니다. 정확한 진단·치료는 의료 전문가에게 문의하세요.
          </p>
        </>
      ) : (
        /* 데이터 없음 */
        <div className="bg-white rounded-[16px] border border-dashed border-border p-8 text-center shadow-sm">
          <p className="text-3xl mb-3" aria-hidden="true">📊</p>
          <p className="text-sm font-semibold text-text-primary mb-1">
            아직 위험도 분석 데이터가 없어요
          </p>
          <p className="text-xs text-text-tertiary mb-4">
            건강 데이터를 입력하면 위험도가 분석돼요
          </p>
          <Link
            href="/health-records"
            className="text-sm font-semibold text-brand-black underline underline-offset-2"
          >
            건강 데이터 입력하기 →
          </Link>
        </div>
      )}
    </section>
  );
}
