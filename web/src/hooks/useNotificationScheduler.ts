"use client";

import { useEffect } from "react";
import { MEDICATION_STORAGE_KEY, type Medication } from "@/components/health/MedicationManager";
import { pushNotification } from "@/components/layout/NotificationDropdown";

const NOTIF_SETTINGS_KEY = "notification-settings";

interface Settings {
  medication: boolean;
  challengeRemind: boolean;
  challengeTime: string;
}

const DEFAULT_SETTINGS: Settings = {
  medication: true,
  challengeRemind: true,
  challengeTime: "20:00",
};

/** 현재 시각 기준으로 특정 HH:MM까지 남은 ms */
function msUntil(timeStr: string): number {
  const [hh, mm] = timeStr.split(":").map(Number);
  const now = new Date();
  const target = new Date(now);
  target.setHours(hh, mm, 0, 0);
  if (target <= now) target.setDate(target.getDate() + 1);
  return target.getTime() - now.getTime();
}

async function sendBrowserNotification(title: string, body: string, tag?: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;

  try {
    if ("serviceWorker" in navigator) {
      const reg = await navigator.serviceWorker.getRegistration("/sw.js");
      if (reg?.active) {
        reg.active.postMessage({ type: "SHOW_NOTIFICATION", title, body, tag });
        return;
      }
    }
  } catch { /* 무시 */ }

  new Notification(title, { body, icon: "/chat-button.png", tag });
}

/**
 * 앱 전역에서 알림 스케줄링.
 * Providers에 마운트되어 페이지 이동과 무관하게 유지.
 */
export function useNotificationScheduler() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    function scheduleAll() {
      // 기존 타이머 전부 제거
      timers.forEach(clearTimeout);
      timers.length = 0;

      let settings: Settings = DEFAULT_SETTINGS;
      try {
        const raw = localStorage.getItem(NOTIF_SETTINGS_KEY);
        if (raw) settings = { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
      } catch { /* 무시 */ }

      // ── 복약 알림 ────────────────────────────────
      // pushNotification(내역 저장)은 권한 무관, 브라우저 알림만 권한 필요
      if (settings.medication) {
        try {
          const raw = localStorage.getItem(MEDICATION_STORAGE_KEY);
          const meds: Medication[] = raw ? JSON.parse(raw) : [];

          meds.filter((m) => m.active).forEach((med) => {
            med.times.forEach((t) => {
              const label = med.dosageAmount
                ? `${med.name} ${med.dosageAmount}${med.dosageUnit}`
                : med.name;

              const id = setTimeout(async () => {
                const title = "💊 복약 알림";
                const body = `${label} 복용 시간이에요!`;
                // 알림 내역에는 항상 저장
                pushNotification({ category: "복약", title, body });
                // 브라우저 알림은 권한 있을 때만
                await sendBrowserNotification(title, body, `med-${med.id}-${t}`);
                scheduleAll();
              }, msUntil(t));

              timers.push(id);
            });
          });
        } catch { /* 무시 */ }
      }

      // ── 챌린지 리마인드 ──────────────────────────
      if (settings.challengeRemind) {
        const id = setTimeout(async () => {
          const title = "🏃 챌린지 리마인드";
          const body = "오늘 챌린지를 아직 완료하지 않았어요. 지금 도전해보세요!";
          pushNotification({ category: "챌린지", title, body });
          await sendBrowserNotification(title, body, "challenge-remind");
          scheduleAll();
        }, msUntil(settings.challengeTime));

        timers.push(id);
      }
    }

    scheduleAll();

    // 같은 탭 내 변경 감지 — 커스텀 이벤트 (storage 이벤트는 타 탭에서만 발생)
    const handleReschedule = () => scheduleAll();
    window.addEventListener("notif-reschedule", handleReschedule);

    // 다른 탭에서의 변경 감지
    const handleStorage = (e: StorageEvent) => {
      if (e.key === NOTIF_SETTINGS_KEY || e.key === MEDICATION_STORAGE_KEY) {
        scheduleAll();
      }
    };
    window.addEventListener("storage", handleStorage);

    return () => {
      timers.forEach(clearTimeout);
      window.removeEventListener("notif-reschedule", handleReschedule);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);
}
