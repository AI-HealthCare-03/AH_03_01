"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

/* ─────────────────────────────────────────────────────
   알림 설정 페이지 — localStorage 저장
───────────────────────────────────────────────────── */

const STORAGE_KEY = "notification-settings";

interface NotificationSettings {
  medication: boolean;
  challengeRemind: boolean;
  challengeTime: string; // "HH:MM" 24시간 형식
  community: boolean;
  riskChange: boolean;
}

const DEFAULT: NotificationSettings = {
  medication: true,
  challengeRemind: true,
  challengeTime: "20:00",
  community: false,
  riskChange: true,
};

/* ── 시간 변환 유틸 ──────────────────────────────────── */
function to12h(time24: string): { period: "오전" | "오후"; hour: string; minute: string } {
  const [h, m] = time24.split(":").map(Number);
  const period: "오전" | "오후" = h < 12 ? "오전" : "오후";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return { period, hour: String(hour12).padStart(2, "0"), minute: String(m).padStart(2, "0") };
}

function to24h(period: "오전" | "오후", hour: string, minute: string): string {
  let h = parseInt(hour, 10);
  if (period === "오전") {
    if (h === 12) h = 0;
  } else {
    if (h !== 12) h += 12;
  }
  return `${String(h).padStart(2, "0")}:${minute}`;
}

/* ── select 스타일 래퍼 ──────────────────────────────── */
function StyledSelect({
  value,
  onChange,
  children,
  width = "auto",
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
  width?: string;
}) {
  return (
    <div className="relative inline-flex items-center">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ minWidth: width }}
        className="h-10 pl-3 pr-8 border border-border rounded-[10px] text-sm font-medium text-text-primary bg-white appearance-none focus:outline-none focus:ring-2 focus:ring-brand-black focus:border-brand-black cursor-pointer transition-colors hover:border-text-secondary"
      >
        {children}
      </select>
      {/* 커스텀 화살표 */}
      <svg
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary"
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
      >
        <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

/* ── 커스텀 시간 선택기 ─────────────────────────────── */
function TimePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const init = to12h(value);
  const [period, setPeriod] = useState<"오전" | "오후">(init.period);
  const [hour, setHour] = useState(init.hour);
  const [minute, setMinute] = useState(init.minute);

  // 외부 value 변경 시 동기화
  useEffect(() => {
    const parsed = to12h(value);
    setPeriod(parsed.period);
    setHour(parsed.hour);
    setMinute(parsed.minute);
  }, [value]);

  const handlePeriodChange = (p: "오전" | "오후") => {
    setPeriod(p);
    onChange(to24h(p, hour, minute));
  };

  const handleHourChange = (newHour: string) => {
    setHour(newHour);
    onChange(to24h(period, newHour, minute));
  };

  const handleMinuteChange = (newMinute: string) => {
    setMinute(newMinute);
    onChange(to24h(period, hour, newMinute));
  };

  const hours = Array.from({ length: 12 }, (_, i) =>
    String(i + 1).padStart(2, "0")
  );
  // 1분 단위 00~59
  const minutes = Array.from({ length: 60 }, (_, i) =>
    String(i).padStart(2, "0")
  );

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* 오전/오후 토글 */}
      <div className="flex rounded-[10px] border border-border overflow-hidden shrink-0 h-10">
        {(["오전", "오후"] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => handlePeriodChange(p)}
            className={[
              "px-3 text-sm font-semibold transition-colors min-w-[52px]",
              period === p
                ? "bg-brand-black text-white"
                : "bg-white text-text-secondary hover:bg-surface",
            ].join(" ")}
          >
            {p}
          </button>
        ))}
      </div>

      {/* 시 선택 */}
      <div className="flex items-center gap-1.5">
        <StyledSelect value={hour} onChange={handleHourChange} width="60px">
          {hours.map((h) => (
            <option key={h} value={h}>{h}</option>
          ))}
        </StyledSelect>
        <span className="text-sm text-text-secondary font-medium">시</span>
      </div>

      {/* 분 선택 — 1분 단위 */}
      <div className="flex items-center gap-1.5">
        <StyledSelect value={minute} onChange={handleMinuteChange} width="60px">
          {minutes.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </StyledSelect>
        <span className="text-sm text-text-secondary font-medium">분</span>
      </div>
    </div>
  );
}

/* ── 토글 스위치 ─────────────────────────────────────── */
function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={[
        "relative inline-flex h-7 w-12 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200",
        checked ? "bg-brand-black" : "bg-border",
      ].join(" ")}
    >
      <span
        className={[
          "pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow transition-transform duration-200",
          checked ? "translate-x-5" : "translate-x-0",
        ].join(" ")}
      />
    </button>
  );
}

/* ── 알림 행 ─────────────────────────────────────────── */
function NotificationRow({
  label,
  description,
  checked,
  onChange,
  children,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  children?: React.ReactNode;
}) {
  return (
    <div className="py-4 border-b border-border last:border-b-0">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-text-primary">{label}</p>
          {description && (
            <p className="text-xs text-text-tertiary mt-0.5">{description}</p>
          )}
        </div>
        <Toggle checked={checked} onChange={onChange} />
      </div>
      {checked && children && <div className="mt-3">{children}</div>}
    </div>
  );
}

/* ── 메인 ─────────────────────────────────────────────── */
export default function NotificationSettingsPage() {
  const [settings, setSettings] = useState<NotificationSettings>(DEFAULT);
  const [saved, setSaved] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setSettings({ ...DEFAULT, ...JSON.parse(raw) });
    } catch { /* 무시 */ }
  }, []);

  const update = <K extends keyof NotificationSettings>(
    key: K,
    value: NotificationSettings[K]
  ) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* 무시 */ }
      return next;
    });
    // 저장됨 표시 — 기존 타이머 초기화 후 3초 유지
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaved(true);
    saveTimer.current = setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Link href="/mypage" className="text-text-tertiary hover:text-text-primary text-lg">
          ←
        </Link>
        <h1 className="text-xl font-black text-text-primary">알림 설정</h1>
        {saved && (
          <span className="ml-auto text-xs text-status-success font-semibold animate-pulse">
            저장됨 ✓
          </span>
        )}
      </div>

      {/* 복약 알림 */}
      <section className="bg-white border border-border rounded-[16px] px-5">
        <p className="text-xs font-bold text-text-tertiary pt-4 pb-2 uppercase tracking-wide">복약</p>
        <NotificationRow
          label="복약 알림"
          description="복용 시간마다 푸시 알림"
          checked={settings.medication}
          onChange={(v) => update("medication", v)}
        >
          <p className="text-xs text-text-tertiary">복약 일정에 등록된 시간에 알림이 전송됩니다.</p>
        </NotificationRow>
      </section>

      {/* 챌린지 알림 */}
      <section className="bg-white border border-border rounded-[16px] px-5">
        <p className="text-xs font-bold text-text-tertiary pt-4 pb-2 uppercase tracking-wide">챌린지</p>
        <NotificationRow
          label="챌린지 리마인드"
          description="설정된 시간에 챌린지 수행 알림"
          checked={settings.challengeRemind}
          onChange={(v) => update("challengeRemind", v)}
        >
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-text-secondary shrink-0">알림 시간</span>
            <TimePicker
              value={settings.challengeTime}
              onChange={(v) => update("challengeTime", v)}
            />
          </div>
        </NotificationRow>
      </section>

      {/* 기타 알림 */}
      <section className="bg-white border border-border rounded-[16px] px-5">
        <p className="text-xs font-bold text-text-tertiary pt-4 pb-2 uppercase tracking-wide">기타</p>
        <NotificationRow
          label="커뮤니티 활동"
          description="댓글·좋아요·신고 답변"
          checked={settings.community}
          onChange={(v) => update("community", v)}
        />
        <NotificationRow
          label="위험도 변화 알림"
          description="위험도 등급이 변할 때"
          checked={settings.riskChange}
          onChange={(v) => update("riskChange", v)}
        />
      </section>

      <p className="text-xs text-text-tertiary text-center px-4">
        웹 푸시 알림으로 우선 제공됩니다. SMS 알림은 추후 유료 옵션 검토 중입니다.
      </p>
    </div>
  );
}
