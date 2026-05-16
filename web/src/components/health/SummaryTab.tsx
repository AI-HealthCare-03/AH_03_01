"use client";

import Link from "next/link";
import { useHealthProfile } from "@/hooks/queries/useHealthProfile";
import { useHealthRecordList } from "@/hooks/queries/useHealthRecordList";
import {
  calcBmi,
  getBmiStatus,
  getBloodPressureStatus,
  getFastingGlucoseStatus,
  getHba1cStatus,
} from "@/lib/health/status";
import StatusBadge from "./StatusBadge";

/* ── 요약 카드 ─────────────────────────── */

interface MetricCardProps {
  label: string;
  value: string | null;
  unit: string;
  sub?: string;
  status: "정상" | "주의" | "위험" | "N/A";
}

function MetricCard({ label, value, unit, sub, status }: MetricCardProps) {
  return (
    <div className="bg-white rounded-[16px] p-4 shadow-[0_1px_4px_rgba(0,0,0,0.08)] flex flex-col gap-2">
      <p className="text-xs text-text-secondary font-medium">{label}</p>
      {value !== null ? (
        <>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-text-primary">{value}</span>
            <span className="text-xs text-text-tertiary">{unit}</span>
          </div>
          <StatusBadge status={status} />
          {sub && <p className="text-xs text-text-tertiary">{sub}</p>}
        </>
      ) : (
        <>
          <p className="text-lg font-bold text-text-tertiary">—</p>
          <StatusBadge status="N/A" />
          <p className="text-xs text-text-tertiary">데이터 없음</p>
        </>
      )}
    </div>
  );
}

/* ── 면책 문구 ─────────────────────────── */

function Disclaimer() {
  return (
    <div className="rounded-[12px] bg-surface border border-border p-4 text-xs text-text-secondary space-y-1">
      <p className="font-semibold text-text-primary">안내 사항</p>
      <p>
        본 결과는 의학적 진단이 아닙니다. 정확한 진단·치료는 의료 전문가에게 문의하세요.
      </p>
      <p className="text-text-tertiary mt-2">
        판정 기준: KSH 2022 고혈압 진료지침 / KDA 2023 당뇨병 진료지침 /
        대한비만학회 BMI 기준 (아시아-태평양 기준)
      </p>
    </div>
  );
}

/* ── 메인 컴포넌트 ─────────────────────── */

export default function SummaryTab() {
  const { data: profile, isLoading: profileLoading } = useHealthProfile();
  const { data: bpList, isLoading: bpLoading } = useHealthRecordList({
    recordType: "BLOOD_PRESSURE",
    size: 1,
  });
  const { data: bgList, isLoading: bgLoading } = useHealthRecordList({
    recordType: "BLOOD_GLUCOSE",
    subType: "FASTING",
    size: 1,
  });
  const { data: hba1cList, isLoading: hba1cLoading } = useHealthRecordList({
    recordType: "HBA1C",
    size: 1,
  });

  const isLoading = profileLoading || bpLoading || bgLoading || hba1cLoading;

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-10 bg-surface rounded-[8px]" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-36 bg-surface rounded-[16px]" />
          ))}
        </div>
      </div>
    );
  }

  /* ── 값 파싱 ── */
  const heightCm = profile?.height_cm ?? null;
  const weightKg = profile?.weight_kg ?? null;
  const bmi =
    heightCm && weightKg ? calcBmi(heightCm, weightKg) : null;

  const latestBp = bpList?.[0] ?? null;
  const sysParsed = latestBp ? parseFloat(latestBp.primary_value) : null;
  const diaParsed = latestBp ? parseFloat(latestBp.secondary_value ?? "0") : null;

  const latestBg = bgList?.[0] ?? null;
  const bgParsed = latestBg ? parseFloat(latestBg.primary_value) : null;

  const latestHba1c = hba1cList?.[0] ?? null;
  const hba1cParsed = latestHba1c ? parseFloat(latestHba1c.primary_value) : null;

  /* 최근 측정일 — 가장 최신 measured_at.
     백엔드 HealthProfileResponse 는 updated_at 을 보내므로 그것을 우선 사용. */
  const dates: number[] = [
    latestBp?.measured_at,
    latestBg?.measured_at,
    latestHba1c?.measured_at,
    profile?.updated_at ?? profile?.recorded_at,
  ]
    .filter((d): d is string => Boolean(d))
    .map((d) => new Date(d).getTime());
  const latestDate =
    dates.length > 0 ? new Date(Math.max(...dates)) : null;

  const hasAnyData = latestDate !== null;

  return (
    <div className="space-y-5">
      {/* 상단 헤더 */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">
          {hasAnyData
            ? `최근 측정 ${latestDate!.toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" })}`
            : "아직 측정 기록이 없습니다"}
        </p>
        <Link
          href="/health-records/new"
          className="flex items-center gap-1 px-3 py-2 bg-brand text-brand-black text-sm font-semibold rounded-[10px] hover:bg-brand-hover transition-colors"
        >
          + 데이터 입력
        </Link>
      </div>

      {/* 빈 상태 */}
      {!hasAnyData && (
        <div className="text-center py-12 space-y-2">
          <p className="text-4xl">📊</p>
          <p className="font-semibold text-text-primary">건강 데이터를 입력해 보세요</p>
          <p className="text-sm text-text-secondary">
            혈압, 혈당, HbA1c 등을 기록하면 맞춤 위험도 분석을 받을 수 있어요.
          </p>
          <Link
            href="/health-records/new"
            className="inline-flex items-center gap-1 mt-3 px-5 py-2.5 bg-brand text-brand-black text-sm font-semibold rounded-[12px] hover:bg-brand-hover transition-colors"
          >
            첫 데이터 입력하기
          </Link>
        </div>
      )}

      {/* 지표 카드 그리드 */}
      {hasAnyData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="BMI"
            value={bmi !== null ? bmi.toFixed(1) : null}
            unit="kg/m²"
            sub={bmi !== null ? "자동 계산" : undefined}
            status={bmi !== null ? getBmiStatus(bmi) : "N/A"}
          />
          <MetricCard
            label="혈압"
            value={
              sysParsed !== null && diaParsed !== null
                ? `${sysParsed.toFixed(0)}/${diaParsed.toFixed(0)}`
                : null
            }
            unit="mmHg"
            status={sysParsed !== null ? getBloodPressureStatus(sysParsed) : "N/A"}
          />
          <MetricCard
            label="공복혈당"
            value={bgParsed !== null ? bgParsed.toFixed(0) : null}
            unit="mg/dL"
            status={bgParsed !== null ? getFastingGlucoseStatus(bgParsed) : "N/A"}
          />
          <MetricCard
            label="HbA1c"
            value={hba1cParsed !== null ? hba1cParsed.toFixed(1) : null}
            unit="%"
            status={hba1cParsed !== null ? getHba1cStatus(hba1cParsed) : "N/A"}
          />
        </div>
      )}

      {/* 위험도 CTA */}
      {hasAnyData && (
        <div className="flex items-center justify-center">
          <Link
            href="/health-records?tab=risk"
            className="text-sm font-semibold text-text-primary hover:underline"
          >
            💡 위험도 자세히 보기 →
          </Link>
        </div>
      )}

      {/* 면책 */}
      <Disclaimer />
    </div>
  );
}
