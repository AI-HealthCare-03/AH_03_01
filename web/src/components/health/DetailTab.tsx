"use client";

import { useState } from "react";
import { useHealthProfile } from "@/hooks/queries/useHealthProfile";
import { useHealthRecordList } from "@/hooks/queries/useHealthRecordList";
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

/* 알코올 빈도 라벨 (백엔드 AlcoholIntake) */
const ALCOHOL_LABEL: Record<string, string> = {
  NONE: "없음",
  LIGHT: "주 1~2회",
  MODERATE: "주 3~4회",
  HEAVY: "매일",
};

/* 임신 상태 라벨 (백엔드 PregnancyHistory) */
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

/* 흡연 위험도 (백엔드 is_smoker bool) */
function getSmokingStatus(isSmoker?: boolean): HealthStatus | "N/A" {
  if (isSmoker === undefined || isSmoker === null) return "N/A";
  return isSmoker ? "위험" : "정상";
}

/* 알코올 위험도 (백엔드 AlcoholIntake) */
function getAlcoholStatus(s?: string): HealthStatus | "N/A" {
  if (!s) return "N/A";
  if (s === "HEAVY") return "위험";
  if (s === "MODERATE") return "주의";
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

  /* 날짜 선택 시 해당 날짜의 체중/허리둘레 기록 조회 */
  const { data: weightRecords } = useHealthRecordList(
    { recordType: "WEIGHT", from: selectedDate, to: selectedDate },
    { enabled: !!selectedDate }
  );
  const { data: waistRecords } = useHealthRecordList(
    { recordType: "WAIST", from: selectedDate, to: selectedDate },
    { enabled: !!selectedDate }
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

  /* 날짜 선택 시 해당 날짜 기록만 사용 (없으면 null), 미선택 시 프로필 기본값 사용 */
  const displayWeightKg: number | null = selectedDate
    ? (weightRecords && weightRecords.length > 0 ? parseFloat(weightRecords[0].primary_value) : null)
    : (profile?.weight_kg != null ? Number(profile.weight_kg) : null);

  const displayWaistCm: number | null = selectedDate
    ? (waistRecords && waistRecords.length > 0 ? parseFloat(waistRecords[0].primary_value) : null)
    : (profile?.waist_cm != null ? Number(profile.waist_cm) : null);

  const bmi =
    profile?.height_cm && displayWeightKg
      ? calcBmi(profile.height_cm, displayWeightKg)
      : null;

  /* 만성질환 표시. 백엔드는 diseases: string[] 사용 (chronic_diseases 아님).
     백엔드 enum 키가 들어오면 한글 라벨로, 자유 문자열이면 그대로 표시. */
  const p = profile as unknown as Record<string, unknown>;
  const diseases = (p?.diseases as string[] | undefined) ?? profile?.chronic_diseases;
  const chronicLabel =
    diseases && diseases.length > 0
      ? diseases.map((d) => CHRONIC_LABEL[d] ?? d).join(", ")
      : null;
  const isSmoker = p?.is_smoker as boolean | undefined;
  const alcoholIntake = p?.alcohol_intake as string | undefined;
  const hasDmFamily = p?.has_diabetes_family_history as boolean | undefined;
  const hasHtnFamily = p?.has_hypertension_family_history as boolean | undefined;
  const pregnancyHistory = p?.pregnancy_history as string | undefined;
  const medications = p?.medications as string[] | undefined;
  const medicationLabel =
    medications && medications.length > 0 ? medications.join(", ") : null;

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
                    : `기록일: ${(() => {
                        const d = profile.updated_at ?? profile.recorded_at;
                        return d ? new Date(d).toLocaleDateString("ko-KR") : "—";
                      })()}`
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
              <DetailRow
                label="신장 / 체중"
                value={
                  profile.height_cm && displayWeightKg
                    ? `${profile.height_cm}cm / ${displayWeightKg}kg`
                    : selectedDate && weightRecords?.length === 0
                    ? "해당 날짜 기록 없음"
                    : null
                }
                status={bmi !== null ? getBmiStatus(bmi) : "N/A"}
              />
              <DetailRow
                label="허리둘레"
                value={
                  displayWaistCm
                    ? `${displayWaistCm}cm`
                    : selectedDate && waistRecords?.length === 0
                    ? "해당 날짜 기록 없음"
                    : null
                }
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
                  isSmoker === undefined ? null : isSmoker ? "현재 흡연" : "비흡연"
                }
                status={getSmokingStatus(isSmoker)}
              />
              <DetailRow
                label="알코올"
                value={
                  alcoholIntake
                    ? ALCOHOL_LABEL[alcoholIntake] ?? alcoholIntake
                    : null
                }
                status={getAlcoholStatus(alcoholIntake)}
              />
              <DetailRow
                label="당뇨 가족력"
                value={
                  hasDmFamily === undefined
                    ? null
                    : hasDmFamily
                    ? "있음"
                    : "없음"
                }
                status={
                  hasDmFamily === undefined ? "N/A" : hasDmFamily ? "주의" : "정상"
                }
              />
              <DetailRow
                label="고혈압 가족력"
                value={
                  hasHtnFamily === undefined
                    ? null
                    : hasHtnFamily
                    ? "있음"
                    : "없음"
                }
                status={
                  hasHtnFamily === undefined ? "N/A" : hasHtnFamily ? "주의" : "정상"
                }
              />
              <DetailRow
                label="임신 경험"
                value={
                  pregnancyHistory
                    ? PREGNANCY_LABEL[pregnancyHistory] ?? pregnancyHistory
                    : null
                }
              />
              <DetailRow label="만성질환" value={chronicLabel} />
              <DetailRow label="복용중인 약" value={medicationLabel} />
            </div>
          </div>
        )}
      </div>

      {/* 우측 사이드 안내 (데스크탑) */}
      <SideGuide />
    </div>
  );
}
