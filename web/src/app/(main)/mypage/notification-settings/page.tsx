"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  MEDICATION_STORAGE_KEY,
  type Medication,
} from "@/components/health/MedicationManager";
import { pushNotification } from "@/components/layout/NotificationDropdown";
import { notifSettingsKey } from "@/lib/notifKeys";

/* ─────────────────────────────────────────────────────
   알림 설정 페이지 — localStorage 저장 + 웹 알림
───────────────────────────────────────────────────── */

interface NotificationSettings {
  medication: boolean;
  challengeRemind: boolean;
  challengeTime: string;
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

/* ── 시간 변환 ──────────────────────────────────────── */
function to12h(time24: string): { period: "오전" | "오후"; hour: string; minute: string } {
  const [h, m] = time24.split(":").map(Number);
  const period: "오전" | "오후" = h < 12 ? "오전" : "오후";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return { period, hour: String(hour12).padStart(2, "0"), minute: String(m).padStart(2, "0") };
}
function to24h(period: "오전" | "오후", hour: string, minute: string): string {
  let h = parseInt(hour, 10);
  if (period === "오전") { if (h === 12) h = 0; }
  else { if (h !== 12) h += 12; }
  return `${String(h).padStart(2, "0")}:${minute}`;
}

/* ── 웹 알림 유틸 ───────────────────────────────────── */

/** 서비스 워커 등록 */
async function registerSW(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) return null;
  try {
    const reg = await navigator.serviceWorker.register("/sw.js");
    return reg;
  } catch {
    return null;
  }
}

/** 알림 권한 요청 */
async function requestPermission(): Promise<boolean> {
  if (!("Notification" in window)) return false;
  if (Notification.permission === "granted") return true;
  const result = await Notification.requestPermission();
  return result === "granted";
}

/** 현재 시각 기준으로 특정 HH:MM까지 남은 ms 계산 (다음 도래 시각) */
function msUntil(timeStr: string): number {
  const [hh, mm] = timeStr.split(":").map(Number);
  const now = new Date();
  const target = new Date(now);
  target.setHours(hh, mm, 0, 0);
  if (target <= now) target.setDate(target.getDate() + 1); // 이미 지났으면 다음날
  return target.getTime() - now.getTime();
}

/** 복약 알림 스케줄링 — 각 약의 복용 시간마다 알림 */
async function scheduleMedicationNotifications() {
  const granted = await requestPermission();
  if (!granted) return;

  const reg = await registerSW();

  try {
    const raw = localStorage.getItem(MEDICATION_STORAGE_KEY);
    const meds: Medication[] = raw ? JSON.parse(raw) : [];
    const active = meds.filter((m) => m.active);

    active.forEach((med) => {
      med.times.forEach((t) => {
        const ms = msUntil(t);
        const label = med.dosageAmount
          ? `${med.name} ${med.dosageAmount}${med.dosageUnit}`
          : med.name;

        setTimeout(() => {
          const title = "💊 복약 알림";
          const body = `${label} 복용 시간이에요!`;
          // 알림 내역 저장
          pushNotification({ category: "복약", title, body });
          if (reg?.active) {
            reg.active.postMessage({ type: "SHOW_NOTIFICATION", title, body, tag: `med-${med.id}-${t}` });
          } else {
            new Notification(title, { body, icon: "/chat-button.png", tag: `med-${med.id}-${t}` });
          }
          scheduleMedicationNotifications();
        }, ms);
      });
    });
  } catch { /* 무시 */ }
}

/** 챌린지 리마인드 알림 스케줄링 */
async function scheduleChallengeNotification(timeStr: string) {
  const granted = await requestPermission();
  if (!granted) return;
  const reg = await registerSW();
  const ms = msUntil(timeStr);

  setTimeout(() => {
    const title = "🏃 챌린지 리마인드";
    const body = "오늘 챌린지를 아직 완료하지 않았어요. 지금 도전해보세요!";
    pushNotification({ category: "챌린지", title, body });
    if (reg?.active) {
      reg.active.postMessage({ type: "SHOW_NOTIFICATION", title, body, tag: "challenge-remind" });
    } else {
      new Notification(title, { body, icon: "/chat-button.png" });
    }
    scheduleChallengeNotification(timeStr);
  }, ms);
}

/* ── select 스타일 래퍼 ─────────────────────────────── */
function StyledSelect({
  value, onChange, children,
}: { value: string; onChange: (v: string) => void; children: React.ReactNode }) {
  return (
    <div className="relative inline-flex items-center">
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="h-10 pl-3 pr-8 border border-border rounded-[10px] text-sm font-medium text-text-primary bg-white appearance-none focus:outline-none focus:ring-2 focus:ring-brand-black focus:border-brand-black cursor-pointer transition-colors hover:border-text-secondary">
        {children}
      </select>
      <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}

/* ── 시간 선택기 ─────────────────────────────────────── */
function TimePicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const init = to12h(value);
  const [period, setPeriod] = useState<"오전" | "오후">(init.period);
  const [hour, setHour] = useState(init.hour);
  const [minute, setMinute] = useState(init.minute);

  useEffect(() => {
    const parsed = to12h(value);
    setPeriod(parsed.period); setHour(parsed.hour); setMinute(parsed.minute);
  }, [value]);

  const emit = (p: "오전" | "오후", h: string, m: string) => onChange(to24h(p, h, m));

  const hours = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, "0"));
  const minutes = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0"));

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex rounded-[10px] border border-border overflow-hidden shrink-0 h-10">
        {(["오전", "오후"] as const).map((p) => (
          <button key={p} type="button" onClick={() => { setPeriod(p); emit(p, hour, minute); }}
            className={["px-3 text-sm font-semibold transition-colors min-w-[52px]",
              period === p ? "bg-brand-black text-white" : "bg-white text-text-secondary hover:bg-surface"].join(" ")}>
            {p}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1.5">
        <StyledSelect value={hour} onChange={(v) => { setHour(v); emit(period, v, minute); }}>
          {hours.map((h) => <option key={h} value={h}>{h}</option>)}
        </StyledSelect>
        <span className="text-sm text-text-secondary font-medium">시</span>
      </div>
      <div className="flex items-center gap-1.5">
        <StyledSelect value={minute} onChange={(v) => { setMinute(v); emit(period, hour, v); }}>
          {minutes.map((m) => <option key={m} value={m}>{m}</option>)}
        </StyledSelect>
        <span className="text-sm text-text-secondary font-medium">분</span>
      </div>
    </div>
  );
}

/* ── 토글 스위치 ─────────────────────────────────────── */
function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      className={["relative inline-flex h-7 w-12 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200",
        checked ? "bg-brand-black" : "bg-border"].join(" ")}>
      <span className={["pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow transition-transform duration-200",
        checked ? "translate-x-5" : "translate-x-0"].join(" ")} />
    </button>
  );
}

/* ── 알림 행 ─────────────────────────────────────────── */
function NotificationRow({ label, description, checked, onChange, children }: {
  label: string; description?: string; checked: boolean;
  onChange: (v: boolean) => void; children?: React.ReactNode;
}) {
  return (
    <div className="py-4 border-b border-border last:border-b-0">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-text-primary">{label}</p>
          {description && <p className="text-xs text-text-tertiary mt-0.5">{description}</p>}
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
  const [permissionDenied, setPermissionDenied] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(notifSettingsKey());
      if (raw) setSettings({ ...DEFAULT, ...JSON.parse(raw) });
    } catch { /* 무시 */ }

    // 페이지 로드 시 저장된 설정에 따라 알림 재스케줄
    try {
      const raw = localStorage.getItem(notifSettingsKey());
      const s: NotificationSettings = raw ? { ...DEFAULT, ...JSON.parse(raw) } : DEFAULT;
      if (s.medication && Notification.permission === "granted") scheduleMedicationNotifications();
      if (s.challengeRemind && Notification.permission === "granted") scheduleChallengeNotification(s.challengeTime);
    } catch { /* 무시 */ }
  }, []);

  const update = async <K extends keyof NotificationSettings>(key: K, value: NotificationSettings[K]) => {
    // 알림 관련 토글 ON 시 권한 요청
    if ((key === "medication" || key === "challengeRemind") && value === true) {
      const granted = await requestPermission();
      if (!granted) {
        setPermissionDenied(true);
        setTimeout(() => setPermissionDenied(false), 4000);
        return;
      }
    }

    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      try {
        localStorage.setItem(notifSettingsKey(), JSON.stringify(next));
        // 같은 탭에서 변경 시 스케줄러에 재실행 신호 전송
        window.dispatchEvent(new CustomEvent("notif-reschedule"));
      } catch { /* 무시 */ }
      return next;
    });

    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaved(true);
    saveTimer.current = setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Link href="/mypage" className="text-text-tertiary hover:text-text-primary text-lg">←</Link>
        <h1 className="text-xl font-black text-text-primary">알림 설정</h1>
        {saved && <span className="ml-auto text-xs text-status-success font-semibold animate-pulse">저장됨 ✓</span>}
      </div>

      {/* 권한 거부 안내 */}
      {permissionDenied && (
        <div className="bg-status-danger-bg border border-status-danger rounded-[12px] px-4 py-3 text-sm text-status-danger">
          브라우저 알림 권한이 필요해요. 주소창 왼쪽 자물쇠 아이콘 → 알림 → 허용으로 변경해 주세요.
        </div>
      )}

      {/* 복약 알림 */}
      <section className="bg-white border border-border rounded-[16px] px-5">
        <p className="text-xs font-bold text-text-tertiary pt-4 pb-2 uppercase tracking-wide">복약</p>
        <NotificationRow
          label="복약 알림"
          description="복약 관리에 등록된 시간마다 브라우저 알림"
          checked={settings.medication}
          onChange={(v) => update("medication", v)}
        >
          <p className="text-xs text-text-tertiary">
            마이페이지 → 복약 관리에 등록된 약의 복용 시간에 맞춰 알림이 전송돼요.
          </p>
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
            <TimePicker value={settings.challengeTime} onChange={(v) => update("challengeTime", v)} />
          </div>
        </NotificationRow>
      </section>

      {/* 기타 알림 */}
      <section className="bg-white border border-border rounded-[16px] px-5">
        <p className="text-xs font-bold text-text-tertiary pt-4 pb-2 uppercase tracking-wide">기타</p>
        <NotificationRow label="커뮤니티 활동" description="댓글·좋아요·신고 답변"
          checked={settings.community} onChange={(v) => update("community", v)} />
        <NotificationRow label="위험도 변화 알림" description="위험도 등급이 변할 때"
          checked={settings.riskChange} onChange={(v) => update("riskChange", v)} />
      </section>

      <p className="text-xs text-text-tertiary text-center px-4">
        브라우저 탭이 열려 있는 동안 알림이 전송돼요. 탭을 닫으면 알림이 중단됩니다.
      </p>
    </div>
  );
}
