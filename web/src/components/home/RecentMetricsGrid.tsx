"use client";

/* =========================================
   최근 측정 데이터 4박스 그리드
   BMI / 혈압 / 공복혈당 / HbA1c
   ========================================= */

import Link from "next/link";
import {
  calcBmi,
  getBmiStatus,
  getBloodPressureStatus,
  getFastingGlucoseStatus,
  statusColorClass,
  type HealthStatus,
} from "@/lib/health/status";
import type {
  HealthProfileRecord,
  MetricStatResponse,
} from "@/types/api";

interface RecentMetricsGridProps {
  healthProfile: HealthProfileRecord | null | undefined;
  bloodPressure: MetricStatResponse | null | undefined;
  fastingGlucose: MetricStatResponse | null | undefined;
  isLoading: boolean;
}

interface MetricBox {
  label: string;
  value: string;
  unit: string;
  status: HealthStatus | null;
  sublabel?: string;
}

function StatusBadge({ status }: { status: HealthStatus }) {
  const cls = statusColorClass[status];
  return (
    <span
      className={[
        "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold",
        cls.bg,
        cls.text,
      ].join(" ")}
      aria-label={`상태: ${status}`}
    >
      {status}
    </span>
  );
}

function MetricCard({ box }: { box: MetricBox }) {
  return (
    <div className="bg-white rounded-[16px] border border-border p-4 flex flex-col gap-2 shadow-sm">
      <p className="text-xs text-text-tertiary font-medium">{box.label}</p>
      <div className="flex items-end gap-1">
        {box.value === "—" ? (
          <span className="text-2xl font-black text-text-disabled">—</span>
        ) : (
          <>
            <span className="text-2xl font-black text-text-primary leading-none">
              {box.value}
            </span>
            {box.unit && (
              <span className="text-xs text-text-tertiary mb-0.5">{box.unit}</span>
            )}
          </>
        )}
      </div>
      {box.sublabel && (
        <p className="text-[10px] text-text-tertiary">{box.sublabel}</p>
      )}
      <div className="flex items-center justify-between mt-auto">
        {box.status ? (
          <StatusBadge status={box.status} />
        ) : (
          <span className="text-[10px] text-text-disabled">데이터 없음</span>
        )}
        <Link
          href="/health-records"
          className="text-[10px] font-medium text-text-tertiary hover:text-text-primary transition-colors"
          aria-label={`${box.label} 입력하기`}
        >
          + 입력
        </Link>
      </div>
    </div>
  );
}

export default function RecentMetricsGrid({
  healthProfile,
  bloodPressure,
  fastingGlucose,
  isLoading,
}: RecentMetricsGridProps) {
  /* BMI 계산 */
  let bmiBox: MetricBox;
  if (
    healthProfile?.height_cm &&
    healthProfile?.weight_kg
  ) {
    const bmiVal = calcBmi(healthProfile.height_cm, healthProfile.weight_kg);
    bmiBox = {
      label: "BMI",
      value: String(bmiVal),
      unit: "kg/m²",
      status: getBmiStatus(bmiVal),
      sublabel: `${healthProfile.weight_kg}kg / ${healthProfile.height_cm}cm`,
    };
  } else {
    bmiBox = { label: "BMI", value: "—", unit: "", status: null };
  }

  /* 혈압 */
  const bpSeries = bloodPressure?.series;
  const lastBp = bpSeries?.[bpSeries.length - 1];
  const bpBox: MetricBox = lastBp
    ? {
        label: "혈압",
        value: `${Math.round(parseFloat(String(lastBp.primary_value)))}/${Math.round(parseFloat(String(lastBp.secondary_value ?? "0")))}`,
        unit: "mmHg",
        status: getBloodPressureStatus(parseFloat(String(lastBp.primary_value))),
      }
    : { label: "혈압", value: "—", unit: "", status: null };

  /* 공복혈당 */
  const fgSeries = fastingGlucose?.series;
  const lastFg = fgSeries?.[fgSeries.length - 1];
  const fgBox: MetricBox = lastFg
    ? {
        label: "공복혈당",
        value: String(Math.round(parseFloat(String(lastFg.primary_value)))),
        unit: "mg/dL",
        status: getFastingGlucoseStatus(parseFloat(String(lastFg.primary_value))),
      }
    : { label: "공복혈당", value: "—", unit: "", status: null };

  const boxes = [bmiBox, bpBox, fgBox];

  return (
    <section aria-labelledby="recent-metrics-heading">
      <div className="flex items-center justify-between mb-4">
        <h2
          id="recent-metrics-heading"
          className="text-base font-bold text-text-primary"
        >
          최근 측정 데이터
        </h2>
        <Link
          href="/health-records"
          className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
        >
          전체 보기 →
        </Link>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-28 bg-white rounded-[16px] border border-border animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {boxes.map((box) => (
            <MetricCard key={box.label} box={box} />
          ))}
        </div>
      )}
    </section>
  );
}
