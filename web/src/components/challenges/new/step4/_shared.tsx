/* =========================================
   Step4 폼 공통 UI 부품
   모든 카테고리 폼에서 재사용
   ========================================= */
"use client";

import type { ChallengeCadence } from "@/types/challenge";

/* ─── 칩 선택 버튼 ─── */
export function Chips<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T | undefined;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-primary mb-2">
        {label}
      </label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={String(opt.value)}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "px-4 py-2 rounded-full text-sm font-medium border-2 transition-all",
              value === opt.value
                ? "border-brand-black bg-brand text-brand-black"
                : "border-border bg-white text-text-secondary hover:border-brand",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── 라디오 카드 선택 ─── */
export function RadioCards<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label?: string;
  options: { value: T; emoji?: string; title: string; desc?: string }[];
  value: T | undefined;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      {label && (
        <label className="block text-sm font-semibold text-text-primary mb-2">
          {label}
        </label>
      )}
      <div className="grid grid-cols-2 gap-3">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "flex flex-col items-center gap-1.5 p-4 rounded-[14px] border-2 transition-all text-center",
              value === opt.value
                ? "border-brand-black bg-white shadow-sm"
                : "border-border bg-white hover:border-brand",
            ].join(" ")}
            aria-pressed={value === opt.value}
          >
            {opt.emoji && (
              <span className="text-2xl" aria-hidden="true">
                {opt.emoji}
              </span>
            )}
            <span className="text-sm font-semibold text-text-primary">
              {opt.title}
            </span>
            {opt.desc && (
              <span className="text-xs text-text-tertiary">{opt.desc}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── 기간 선택 (7/14/30일) ─── */
export const DURATION_OPTIONS: { value: 7 | 14 | 30; label: string }[] = [
  { value: 7, label: "7일" },
  { value: 14, label: "14일" },
  { value: 30, label: "한 달" },
];

/** 챌린지 기본 기간 (7/14/30일).
 *  WizardFormState.duration_days 는 90/180 까지 허용하지만 (체중 관리 전용),
 *  이 컴포넌트가 받는 값은 7/14/30 만. 호출 측에서 안전하게 narrow. */
export function DurationPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: 7 | 14 | 30) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-primary mb-2">
        챌린지 기간
      </label>
      <div className="flex gap-2">
        {DURATION_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "flex-1 py-2.5 rounded-[10px] text-sm font-semibold border-2 transition-all",
              value === opt.value
                ? "border-brand-black bg-brand text-brand-black"
                : "border-border bg-white text-text-secondary hover:border-brand",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── 주간 기간 (1주일 고정) 안내 ─── */
export function WeeklyDurationNote() {
  return (
    <div className="p-3 bg-surface rounded-[10px]">
      <p className="text-xs text-text-secondary">
        기간: 오늘부터 7일 (1주일 고정)
      </p>
    </div>
  );
}

/* ─── 챌린지 이름 입력 ─── */
export function TitleInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label
        htmlFor="challenge-title"
        className="block text-sm font-semibold text-text-primary mb-2"
      >
        챌린지 이름
      </label>
      <input
        id="challenge-title"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={40}
        className="w-full h-12 px-4 rounded-[12px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white"
        placeholder="챌린지 이름을 입력하세요"
      />
      <p className="text-xs text-text-tertiary mt-1 text-right">
        {value.length}/40
      </p>
    </div>
  );
}

/* ─── 그룹 최대 참여 인원 슬라이더 ─── */
export function MaxParticipantsSlider({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label
        htmlFor="max-participants"
        className="block text-sm font-semibold text-text-primary mb-2"
      >
        최대 참여 인원{" "}
        <span className="font-bold text-brand-black">{value}명</span>
      </label>
      <input
        id="max-participants"
        type="range"
        min={2}
        max={5}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full accent-brand-black"
        aria-label={`최대 참여 인원 ${value}명`}
      />
      <div className="flex justify-between text-xs text-text-tertiary mt-1">
        <span>2명</span>
        <span>5명</span>
      </div>
    </div>
  );
}

/* ─── 예상 보상 카드 ─── */
export function RewardPreview({
  durationDays,
  isGroup,
}: {
  durationDays: number;
  isGroup: boolean;
}) {
  const dailyPts = 70;
  const basePts = dailyPts * durationDays + 200;
  const total = basePts + (isGroup ? 500 : 0);

  return (
    <div className="rounded-[14px] border border-brand bg-brand/10 p-4">
      <p className="text-sm font-bold text-brand-black mb-3">
        예상 보상 미리보기
      </p>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">
            데일리 인증 × {durationDays}일
          </span>
          <span className="font-semibold">최대 {dailyPts * durationDays}P</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">기간 완주 보너스</span>
          <span className="font-semibold">200P</span>
        </div>
        {isGroup && (
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">그룹 전체 완주 보너스</span>
            <span className="font-semibold">500P</span>
          </div>
        )}
        <div className="border-t border-brand/30 pt-2 flex justify-between text-sm font-bold">
          <span>최대 획득 예상</span>
          <span className="text-brand-black">{total}P</span>
        </div>
      </div>
    </div>
  );
}

/* ─── 합산 횟수 칩 (그룹 GROUP_SUM 공통) ─── */
export const GROUP_SUM_OPTIONS = [
  { value: 6, label: "6회" },
  { value: 15, label: "15회" },
  { value: 30, label: "30회" },
  { value: 35, label: "35회" },
];

/* ─── 달성 인원 칩 (그룹 GROUP_MEMBERS 공통) ─── */
export const GROUP_MEMBERS_OPTIONS = [
  { value: 2, label: "2명" },
  { value: 3, label: "3명" },
  { value: 4, label: "4명" },
  { value: 5, label: "5명" },
];

/* ─── 주간 횟수 칩 (1~7회) ─── */
export const WEEKLY_COUNT_OPTIONS = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
  value: n,
  label: `주 ${n}회`,
}));

/* ─── Step4 헤더 ─── */
export function Step4Header() {
  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">목표 설정</h2>
      <p className="text-sm text-text-secondary">
        구체적인 목표를 설정하면 달성하기 쉬워요
      </p>
    </div>
  );
}

/* ─── cadence 자동 결정 헬퍼 ─── */
export function resolveCadence(
  scope: "PERSONAL" | "GROUP",
  step3Mode: string | null
): ChallengeCadence {
  if (scope === "GROUP") {
    /* DISEASE_CARE / NO_SMOKING / NO_ALCOHOL / WEIGHT 그룹은 GROUP_MEMBERS */
    return "GROUP_SUM";
  }
  if (step3Mode === "WEEKLY_COUNT") return "WEEKLY_COUNT";
  return "DAILY";
}
