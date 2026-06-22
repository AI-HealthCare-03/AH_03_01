"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { useHealthProfile } from "@/hooks/queries/useHealthProfile";
import { useHealthRecordList } from "@/hooks/queries/useHealthRecordList";
import {
  calcBmi,
  getBmiStatus,
  getBloodPressureStatus,
  getFastingGlucoseStatus,
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
  const [selectedDate, setSelectedDate] = useState("");
  const today = format(new Date(), "yyyy-MM-dd");
  const hasDateFilter = selectedDate !== "";

  const { data: profile, isLoading: profileLoading } = useHealthProfile();

  /* 최신 기록 쿼리 (항상 실행) */
  const { data: bpList, isLoading: bpLoading } = useHealthRecordList({
    recordType: "BLOOD_PRESSURE",
    size: 1,
  });
  const { data: bgList, isLoading: bgLoading } = useHealthRecordList({
    recordType: "BLOOD_GLUCOSE",
    subType: "FASTING",
    size: 1,
  });
  const { data: weightList } = useHealthRecordList({
    recordType: "WEIGHT",
    size: 1,
  });
  /* 날짜 지정 쿼리 — 선택일 기준 최신값(measured_at ≤ 선택일). 그날 업데이트 안 된 지표는
     그날 기준 가장 최근 확인 수치를 보여준다. */
  const { data: bpDateList } = useHealthRecordList(
    { recordType: "BLOOD_PRESSURE", to: selectedDate, size: 1 },
    { enabled: hasDateFilter }
  );
  const { data: bgDateList } = useHealthRecordList(
    { recordType: "BLOOD_GLUCOSE", subType: "FASTING", to: selectedDate, size: 1 },
    { enabled: hasDateFilter }
  );
  const { data: weightDateList } = useHealthRecordList(
    { recordType: "WEIGHT", to: selectedDate, size: 1 },
    { enabled: hasDateFilter }
  );
  /* 선택 날짜에 입력된 데이터(전 타입)가 하나도 없으면 '데이터 없음'. */
  const { data: dateAnyList, isLoading: dateAnyLoading } = useHealthRecordList(
    { from: selectedDate, to: selectedDate },
    { enabled: hasDateFilter }
  );

  const isLoading = profileLoading || bpLoading || bgLoading;

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-10 bg-surface rounded-[8px]" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-36 bg-surface rounded-[16px]" />
          ))}
        </div>
      </div>
    );
  }

  /* 선택 날짜에 입력 데이터가 전혀 없으면 모든 지표를 '데이터 없음'으로 표시. */
  /* 로딩 중에는 '데이터 없음' 으로 단정하지 않는다(undefined → length 0 오판으로 깜빡임 방지). */
  const noDataForDate = hasDateFilter && !dateAnyLoading && (dateAnyList?.length ?? 0) === 0;

  /* ── 활성 레코드 (날짜 필터 적용 여부에 따라 선택) ── */
  const activeBp = noDataForDate ? null : hasDateFilter ? (bpDateList?.[0] ?? null) : (bpList?.[0] ?? null);
  const activeBg = noDataForDate ? null : hasDateFilter ? (bgDateList?.[0] ?? null) : (bgList?.[0] ?? null);

  /* ── 값 파싱 ── */
  /* 숫자 파싱 — 비정상 문자열(NaN·Infinity)은 null 로 떨궈 'NaN' 표시를 막는다. */
  const recNum = (s?: string | null): number | null => {
    const v = parseFloat(s ?? "");
    return isFinite(v) ? v : null;
  };
  const heightCm = profile?.height_cm ?? null;
  /* 디폴트(날짜 미선택)도 최신 체중 '기록' 우선 — 프로필 체중은 갱신이 드물어,
     오늘 체중을 기록해도 프로필이 옛 값이면 BMI 가 어제처럼 보이던 문제를 막는다.
     (혈압·혈당 카드가 최신 기록을 쓰는 것과 동일한 기준으로 통일.) */
  const latestWeightKg = recNum(weightList?.[0]?.primary_value) ?? (profile?.weight_kg ?? null);
  const dateWeightKg = recNum(weightDateList?.[0]?.primary_value);
  const weightKg = noDataForDate ? null : hasDateFilter ? dateWeightKg : latestWeightKg;
  const bmi = heightCm && weightKg ? calcBmi(heightCm, weightKg) : null;

  const sysParsed = activeBp ? recNum(activeBp.primary_value) : null;
  const diaParsed = activeBp ? recNum(activeBp.secondary_value) : null;
  const bgParsed = activeBg ? recNum(activeBg.primary_value) : null;

  /* 최근 측정일 — 날짜 필터가 없을 때만 계산 */
  const latestBp = bpList?.[0] ?? null;
  const latestBg = bgList?.[0] ?? null;
  const dates: number[] = [
    latestBp?.measured_at,
    latestBg?.measured_at,
    weightList?.[0]?.measured_at,
    profile?.updated_at ?? profile?.recorded_at,
  ]
    .filter((d): d is string => Boolean(d))
    .map((d) => new Date(d).getTime());
  const latestDate = dates.length > 0 ? new Date(Math.max(...dates)) : null;
  const hasAnyData = latestDate !== null;

  return (
    <div className="space-y-5">
      {/* 상단 헤더 */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-sm text-text-secondary">
          {hasDateFilter
            ? noDataForDate
              ? `${selectedDate} · 입력된 데이터 없음`
              : `${selectedDate} 기록`
            : hasAnyData
            ? `최근 측정 ${latestDate!.toLocaleDateString("ko-KR", {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
              })}`
            : "아직 측정 기록이 없습니다"}
        </p>
        <div className="flex items-center gap-2">
          {/* 날짜 선택 */}
          <div className="flex items-center gap-1">
            <input
              type="date"
              max={today}
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="text-xs border border-border rounded-[8px] px-2 py-1.5 text-text-secondary bg-white focus:outline-none focus:border-text-primary"
            />
            {hasDateFilter && (
              <button
                onClick={() => setSelectedDate("")}
                className="text-xs text-text-tertiary hover:text-text-primary px-1 py-1.5"
                aria-label="날짜 필터 초기화"
              >
                ✕
              </button>
            )}
          </div>
          <Link
            href="/health-records/new"
            className="flex items-center gap-1 px-3 py-2 bg-brand text-brand-black text-sm font-semibold rounded-[10px] hover:bg-brand-hover transition-colors"
          >
            + 데이터 입력
          </Link>
        </div>
      </div>

      {/* 빈 상태 */}
      {!hasAnyData && (
        <div className="text-center py-12 space-y-2">
          <p className="text-4xl">📊</p>
          <p className="font-semibold text-text-primary">건강 데이터를 입력해 보세요</p>
          <p className="text-sm text-text-secondary">
            혈압, 혈당 등을 기록하면 맞춤 위험도 분석을 받을 수 있어요.
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
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <MetricCard
            label="BMI"
            value={bmi !== null ? bmi.toFixed(1) : null}
            unit="kg/m²"
            sub={bmi !== null ? (hasDateFilter ? "해당 날짜 체중 기준" : "자동 계산") : undefined}
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
