"use client";

import { useState } from "react";
import { useHealthProfile } from "@/hooks/queries/useHealthProfile";
import { useHealthRecordList } from "@/hooks/queries/useHealthRecordList";
import { MEDICATION_STORAGE_KEY, type Medication } from "@/components/health/MedicationManager";
import StatusBadge from "./StatusBadge";
import WaistPopover from "./WaistPopover";
import type { HealthStatus } from "@/lib/health/status";
import { getBmiStatus, calcBmi } from "@/lib/health/status";
import type { HealthProfileDetail } from "@/types/health";

/* ── 허리둘레 판정 ─────────────────────── */

function getWaistStatus(
  waist: number,
  gender: "MALE" | "FEMALE" | undefined
): HealthStatus {
  if (gender === "MALE") {
    if (waist >= 90) return "위험";
    if (waist >= 80) return "주의";
    return "정상";
  }
  if (gender === "FEMALE") {
    if (waist >= 85) return "위험";
    if (waist >= 75) return "주의";
    return "정상";
  }
  /* 성별 모를 경우 KSSO 혼합 기준 */
  return waist >= 90 ? "위험" : waist >= 80 ? "주의" : "정상";
}

/* 음주 빈도 라벨 (백엔드 alcohol_freq_y BD1_11 코드) */
const ALCOHOL_FREQ_LABEL: Record<number, string> = {
  1: "전혀 안 마심",
  2: "월 1회 미만",
  3: "월 1회 정도",
  4: "월 2~4회",
  5: "주 2~3회",
  6: "주 4회 이상",
};

/* 임신 상태 라벨 (백엔드 PregnancyStatus) */
const PREGNANCY_LABEL: Record<string, string> = {
  NONE: "임신/출산 없음",
  PREGNANT: "임신 중",
  POSTPARTUM: "산후",
  NOT_APPLICABLE: "해당 없음",
};

/* 만성질환 라벨 */
const CHRONIC_LABEL: Record<string, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨병",
  HYPERLIPIDEMIA: "고지혈증",
  HEART_DISEASE: "심장 질환",
  KIDNEY_DISEASE: "신장 질환",
  OBESITY: "비만",
  NONE: "없음",
};

/* 흡연 위험도 (백엔드 current_smoker: 1=흡연, 0=비흡연) */
function getSmokingStatus(currentSmoker?: number | null): HealthStatus | "N/A" {
  if (currentSmoker === undefined || currentSmoker === null) return "N/A";
  return currentSmoker === 1 ? "위험" : "정상";
}

/* 음주 위험도 (백엔드 alcohol_freq_y: 1=안마심 … 6=주4회이상) */
function getAlcoholStatus(freqCode?: number | null): HealthStatus | "N/A" {
  if (freqCode === undefined || freqCode === null) return "N/A";
  if (freqCode >= 6) return "위험";
  if (freqCode >= 5) return "주의";
  return "정상";
}

/* ── 행 컴포넌트 ─────────────────────────── */

interface DetailRowProps {
  label: string;
  value: string | null;
  status?: HealthStatus | "N/A";
  helpTip?: React.ReactNode;
}

function DetailRow({ label, value, status, helpTip }: DetailRowProps) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-none">
      <div className="flex items-center gap-1 text-sm text-text-secondary min-w-0">
        <span>{label}</span>
        {helpTip}
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-4">
        <span className="text-sm font-semibold text-text-primary">
          {value ?? "—"}
        </span>
        {status && <StatusBadge status={status} />}
      </div>
    </div>
  );
}

/* ── 우측 사이드 안내 ─────────────────────── */

function SideGuide() {
  return (
    <div className="hidden md:block space-y-4 min-w-[240px]">
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <h3 className="font-bold text-sm text-text-primary mb-3">판정 기준 안내</h3>
        <ul className="text-xs text-text-secondary space-y-1.5">
          <li>BMI: 18.5~22.9 정상 / 23~24.9 과체중(주의) / ≥25 비만(위험)</li>
          <li>허리둘레: 남성 &lt;80 정상 / 여성 &lt;75 정상</li>
          <li>흡연: 비흡연 정상 / 금연 중 주의 / 현재흡연 위험</li>
          <li>알코올: 주 1~2회 이하 정상 / 주 3~4회 주의 / 매일 위험</li>
        </ul>
      </div>
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)]">
        <h3 className="font-bold text-sm text-text-primary mb-3">데이터 출처</h3>
        <ul className="text-xs text-text-secondary space-y-1">
          <li>KSH 2022 고혈압 진료지침</li>
          <li>KDA 2023 당뇨병 진료지침</li>
          <li>KSSO 2022 비만 진료지침</li>
          <li>KSoLA 2022 이상지질혈증 진료지침</li>
        </ul>
      </div>
    </div>
  );
}

/* ── 메인 컴포넌트 ─────────────────────────── */

export default function DetailTab() {
  const [selectedDate, setSelectedDate] = useState<string>("");
  const today = new Date().toISOString().slice(0, 10);

  const { data: rawProfile, isLoading } = useHealthProfile() as {
    data: HealthProfileDetail | null | undefined;
    isLoading: boolean;
  };

  const hasDate = !!selectedDate;
  /* 디폴트(날짜 미선택): 각 지표의 최신 기록 — 프로필은 갱신이 드물어 옛 값(과 옛 기록일)이
     디폴트로 떠 실제 저장한 적 없는 날짜처럼 보이던 문제 방지. 오늘 업데이트가 있으면 오늘 값. */
  const { data: latestWeight } = useHealthRecordList({ recordType: "WEIGHT", size: 1 });
  const { data: latestWaist } = useHealthRecordList({ recordType: "WAIST", size: 1 });
  /* 날짜 선택 시: 선택일 기준 최신값(measured_at ≤ 선택일) — 그날 업데이트 안 된 항목은
     그날 기준 가장 최근 확인 수치를 보여준다. */
  const { data: asOfWeight } = useHealthRecordList(
    { recordType: "WEIGHT", to: selectedDate, size: 1 },
    { enabled: hasDate }
  );
  const { data: asOfWaist } = useHealthRecordList(
    { recordType: "WAIST", to: selectedDate, size: 1 },
    { enabled: hasDate }
  );
  /* 선택 날짜에 입력된 데이터(전 타입)가 하나도 없으면 '데이터 없음' 안내. */
  const { data: dateAnyRecords } = useHealthRecordList(
    { from: selectedDate, to: selectedDate },
    { enabled: hasDate }
  );

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-12 bg-surface rounded-[8px]" />
        ))}
      </div>
    );
  }

  const profile = rawProfile as HealthProfileDetail | null;

  /* 선택 날짜에 입력 데이터가 전혀 없으면 '데이터 없음'으로 안내(데이터 row 미표시). */
  const noDataForDate = hasDate && (dateAnyRecords?.length ?? 0) === 0;

  const recVal = (list?: { primary_value: string }[]): number | null => {
    const v = parseFloat(list?.[0]?.primary_value ?? "");
    return isFinite(v) ? v : null;
  };
  const profileWeight = profile?.weight_kg != null ? Number(profile.weight_kg) : null;
  const profileWaist = profile?.waist_cm != null ? Number(profile.waist_cm) : null;

  /* 체중/허리둘레: 날짜 선택 시 선택일 기준 최신값(≤선택일), 미선택 시 최신 기록. 둘 다 프로필 폴백. */
  const displayWeightKg: number | null = noDataForDate
    ? null
    : hasDate
      ? (recVal(asOfWeight) ?? profileWeight)
      : (recVal(latestWeight) ?? profileWeight);
  const displayWaistCm: number | null = noDataForDate
    ? null
    : hasDate
      ? (recVal(asOfWaist) ?? profileWaist)
      : (recVal(latestWaist) ?? profileWaist);

  const bmi =
    profile?.height_cm && displayWeightKg
      ? calcBmi(profile.height_cm, displayWeightKg)
      : null;

  /* v2 필드 매핑 — 체중/허리둘레만 해당 날짜 기록 기준. 흡연·음주·가족력·임신·만성질환·복약은
     시계열이 아닌 정적 프로필 항목이라 날짜와 무관하게 항상 현재 프로필 값을 표시한다.
     (이전에는 날짜 선택 시 null 로 비워 N/A 가 떠, 과거 날짜 조회 시 정상 데이터가 사라졌다.) */
  const chronicLabel =
    profile?.chronic_diseases && profile.chronic_diseases.length > 0
      ? profile.chronic_diseases.map((d) => CHRONIC_LABEL[d] ?? d).join(", ")
      : null;
  const currentSmoker = profile?.current_smoker;
  const alcoholFreqY = profile?.alcohol_freq_y;
  const familyDm = profile?.family_dm;
  const familyHp = profile?.family_hp;
  const pregnancyStatus = profile?.pregnancy_status;
  const medications = ((): string[] | null => {
    // 정적 프로필 항목: 백엔드 프로필 우선, 미동기화 시 localStorage 활성 약 목록 fallback.
    if (profile?.medications && profile.medications.length > 0) return profile.medications;
    try {
      const raw = localStorage.getItem(MEDICATION_STORAGE_KEY);
      if (!raw) return null;
      const list = JSON.parse(raw) as Medication[];
      const names = list.filter((m) => m.active).map((m) => m.name);
      return names.length > 0 ? names : null;
    } catch { return null; }
  })();
  const medicationLabel =
    medications && medications.length > 0 ? medications.join(", ") : null;

  /* 디폴트 기록일 = 최신 체중/허리둘레 기록일(없으면 프로필 갱신일). 프로필 updated_at 만
     쓰면 실제 측정 안 한 날이 기록일로 떠 혼란스러웠다. */
  const defaultRecordedAt = (() => {
    const ds = [
      latestWeight?.[0]?.measured_at,
      latestWaist?.[0]?.measured_at,
      profile?.updated_at ?? profile?.recorded_at,
    ]
      .filter((d): d is string => Boolean(d))
      .map((d) => new Date(d).getTime());
    return ds.length ? new Date(Math.max(...ds)) : null;
  })();

  /* 빈 상태 */
  const isEmpty = !profile;

  return (
    <div className="flex gap-6">
      {/* 메인 콘텐츠 */}
      <div className="flex-1 min-w-0">
        {isEmpty ? (
          <div className="text-center py-12 space-y-2">
            <p className="text-4xl">📋</p>
            <p className="font-semibold text-text-primary">건강 기본 정보가 없습니다</p>
            <p className="text-sm text-text-secondary">
              키, 몸무게, 생활습관 정보를 입력하면 더 정확한 위험도를 확인할 수 있어요.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-[16px] shadow-[0_1px_4px_rgba(0,0,0,0.08)] overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-start justify-between gap-3">
              <div>
                <h2 className="font-bold text-text-primary">건강 기본 정보</h2>
                <p className="text-xs text-text-tertiary mt-0.5">
                  {selectedDate
                    ? `조회 날짜: ${new Date(selectedDate).toLocaleDateString("ko-KR")}`
                    : `기록일: ${defaultRecordedAt ? defaultRecordedAt.toLocaleDateString("ko-KR") : "—"}`
                  }
                </p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <label htmlFor="detail-date-picker" className="text-[10px] text-text-tertiary whitespace-nowrap">날짜 선택</label>
                <input
                  id="detail-date-picker"
                  type="date"
                  value={selectedDate}
                  max={today}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="text-xs border border-border rounded-lg px-2 py-1.5 cursor-pointer text-text-secondary hover:border-text-primary focus:outline-none focus:border-text-primary transition-colors"
                />
                {selectedDate && (
                  <button
                    type="button"
                    onClick={() => setSelectedDate("")}
                    className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
                    aria-label="날짜 초기화"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
            <div className="px-5">
              {noDataForDate ? (
                <div className="py-10 text-center space-y-1">
                  <p className="text-2xl">🗓️</p>
                  <p className="text-sm font-semibold text-text-primary">
                    선택한 날짜에 입력된 데이터가 없습니다
                  </p>
                  <p className="text-xs text-text-tertiary">
                    다른 날짜를 선택하거나 ✕ 로 최신 기록을 확인하세요.
                  </p>
                </div>
              ) : (
                <>
              <DetailRow
                label="신장 / 체중"
                value={
                  profile.height_cm && displayWeightKg
                    ? `${profile.height_cm}cm / ${displayWeightKg}kg`
                    : null
                }
                status={bmi !== null ? getBmiStatus(bmi) : "N/A"}
              />
              <DetailRow
                label="허리둘레"
                value={displayWaistCm ? `${displayWaistCm}cm` : null}
                status={
                  displayWaistCm
                    ? getWaistStatus(displayWaistCm, undefined)
                    : "N/A"
                }
                helpTip={<WaistPopover />}
              />
              <DetailRow
                label="흡연"
                value={
                  currentSmoker === undefined || currentSmoker === null
                    ? null
                    : currentSmoker === 1
                    ? "현재 흡연"
                    : "비흡연"
                }
                status={getSmokingStatus(currentSmoker)}
              />
              <DetailRow
                label="알코올"
                value={
                  alcoholFreqY != null
                    ? (ALCOHOL_FREQ_LABEL[alcoholFreqY] ?? String(alcoholFreqY))
                    : null
                }
                status={getAlcoholStatus(alcoholFreqY)}
              />
              <DetailRow
                label="당뇨 가족력"
                value={
                  familyDm === undefined || familyDm === null
                    ? null
                    : familyDm === 1
                    ? "있음"
                    : familyDm === 0
                    ? "없음"
                    : "모름"
                }
                status={
                  familyDm === undefined || familyDm === null
                    ? "N/A"
                    : familyDm === 1
                    ? "주의"
                    : "정상"
                }
              />
              <DetailRow
                label="고혈압 가족력"
                value={
                  familyHp === undefined || familyHp === null
                    ? null
                    : familyHp === 1
                    ? "있음"
                    : familyHp === 0
                    ? "없음"
                    : "모름"
                }
                status={
                  familyHp === undefined || familyHp === null
                    ? "N/A"
                    : familyHp === 1
                    ? "주의"
                    : "정상"
                }
              />
              <DetailRow
                label="임신 경험"
                value={
                  pregnancyStatus
                    ? (PREGNANCY_LABEL[pregnancyStatus] ?? pregnancyStatus)
                    : null
                }
              />
              <DetailRow label="만성질환" value={chronicLabel} />
              <DetailRow label="복용중인 약" value={medicationLabel} />
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 우측 사이드 안내 (데스크탑) */}
      <SideGuide />
    </div>
  );
}
