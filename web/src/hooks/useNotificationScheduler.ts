"use client";

import { useEffect, useRef } from "react";
import { MEDICATION_STORAGE_KEY, type Medication } from "@/components/health/MedicationManager";
import { pushNotification } from "@/components/layout/NotificationDropdown";
import { notifKickPollKey, notifLastSeenKey, notifRiskPollKey, notifSettingsKey, notifSocialPollKey } from "@/lib/notifKeys";
import { listNotifications } from "@/lib/api/notifications";
import { useAuthStore } from "@/stores/auth";

/** @deprecated notifLastSeenKey() 를 사용하세요 */
export const LAST_SEEN_KEY = "notif-last-seen";
const MAX_REPLAY_MS = 7 * 86_400_000; // 최대 7일 소급

/** 마지막 접속 이후 놓친 알림을 소급 생성 */
function replayMissed(settings: Settings) {
  const raw = localStorage.getItem(notifLastSeenKey());
  if (!raw) return;
  const lastSeen = parseInt(raw);
  const now = Date.now();
  if (now - lastSeen < 60_000) return; // 1분 미만이면 스킵

  const from = Math.max(lastSeen, now - MAX_REPLAY_MS);

  if (settings.challengeRemind) {
    const [hh, mm] = settings.challengeTime.split(":").map(Number);
    const dt = new Date(from);
    dt.setHours(hh, mm, 0, 0);
    if (dt.getTime() <= from) dt.setDate(dt.getDate() + 1);
    while (dt.getTime() < now) {
      pushNotification(
        { category: "챌린지", title: "🏃 챌린지 리마인드", body: "오늘 챌린지를 아직 완료하지 않았어요." },
        dt.getTime(),
      );
      dt.setDate(dt.getDate() + 1);
    }
  }

  if (settings.medication) {
    try {
      const meds: Medication[] = JSON.parse(localStorage.getItem(MEDICATION_STORAGE_KEY) ?? "[]");
      meds.filter((m) => m.active).forEach((med) => {
        const label = med.dosageAmount ? `${med.name} ${med.dosageAmount}${med.dosageUnit}` : med.name;
        med.times.forEach((t) => {
          const [hh, mm] = t.split(":").map(Number);
          const dt = new Date(from);
          dt.setHours(hh, mm, 0, 0);
          if (dt.getTime() <= from) dt.setDate(dt.getDate() + 1);
          while (dt.getTime() < now) {
            const dayOfWeek = dt.getDay();
            const shouldNotify =
              med.scheduleType !== "specific_days" ||
              med.scheduleDays.includes(dayOfWeek);
            if (shouldNotify) {
              pushNotification(
                { category: "복약", title: "💊 복약 알림", body: `${label} 복용 시간이었어요.` },
                dt.getTime(),
              );
            }
            dt.setDate(dt.getDate() + 1);
          }
        });
      });
    } catch { /* 무시 */ }
  }
}

interface Settings {
  medication: boolean;
  challengeRemind: boolean;
  challengeTime: string;
  challengeInteraction: boolean;
  community: boolean;
}

const DEFAULT_SETTINGS: Settings = {
  medication: true,
  challengeRemind: true,
  challengeTime: "20:00",
  challengeInteraction: false,
  community: false,
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
  const firstRunRef = useRef(true);
  const scheduleAllRef = useRef<(() => void) | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const kickPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const riskPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (typeof window === "undefined") return;
    // 로그아웃 상태에서는 알림 폴링을 시작하지 않는다. 인증이 필요한 /notifications 폴이
    // 401 을 받으면 전역 401 인터셉터가 /login 으로 강제 이동시켜, 가입·비밀번호 재설정 등
    // 로그아웃 공개 흐름이 30초마다 끊긴다. 로그인하면 isAuthenticated 변화로 다시 셋업된다.
    if (!isAuthenticated) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    function scheduleAll() {
      // 기존 타이머 전부 제거
      timers.forEach(clearTimeout);
      timers.length = 0;

      let settings: Settings = DEFAULT_SETTINGS;
      try {
        const raw = localStorage.getItem(notifSettingsKey());
        if (raw) settings = { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
      } catch { /* 무시 */ }

      // 최초 1회(또는 로그인 직후): 놓친 알림 소급 생성 후 last_seen 갱신
      if (firstRunRef.current) {
        replayMissed(settings);
        firstRunRef.current = false;
      }
      localStorage.setItem(notifLastSeenKey(), Date.now().toString());

      // ── 복약 알림 ────────────────────────────────
      // pushNotification(내역 저장)은 권한 무관, 브라우저 알림만 권한 필요
      if (settings.medication) {
        try {
          const raw = localStorage.getItem(MEDICATION_STORAGE_KEY);
          const meds: Medication[] = raw ? JSON.parse(raw) : [];

          meds.filter((m) => m.active).forEach((med) => {
            const todayDow = new Date().getDay();
            const scheduledToday =
              med.scheduleType !== "specific_days" ||
              med.scheduleDays.includes(todayDow);

            if (!scheduledToday) return;

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

      // ── 소셜 알림 폴링 (챌린지 소통 / 커뮤니티) ──
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (settings.challengeInteraction || settings.community) {
        const poll = async () => {
          try {
            const lastPoll = localStorage.getItem(notifSocialPollKey())
              ?? new Date(Date.now() - 60_000).toISOString();
            const now = new Date().toISOString();
            const notifs = await listNotifications(lastPoll);
            localStorage.setItem(notifSocialPollKey(), now);

            for (const n of notifs) {
              const isChallenge = n.target_type === "VERIFICATION";
              const isCommunity = n.target_type === "POST" || n.target_type === "COMMENT";
              if (n.notification_type === "RISK_CHANGE") continue; // 독립 riskPoll에서 처리
              // KICK/INVITE/DELETE 는 kickPoll 에서 독립 처리 — 소셜 폴링에서 중복/오표시 방지
              if (n.notification_type === "CHALLENGE_KICK" || n.notification_type === "CHALLENGE_INVITE" || n.notification_type === "CHALLENGE_DELETE") continue;
              if (isChallenge && !settings.challengeInteraction) continue;
              if (isCommunity && !settings.community) continue;

              const category = isCommunity ? "커뮤니티" : "챌린지";
              const title = n.notification_type === "LIKE"
                ? "❤️ 좋아요"
                : n.notification_type === "REPLY"
                ? "💬 새 답글"
                : "💬 새 댓글";
              pushNotification({ category, title, body: n.message });
              await sendBrowserNotification(title, n.message);
            }
          } catch { /* 무시 */ }
        };
        pollIntervalRef.current = setInterval(poll, 30_000);
      }

      // ── 위험도 변화 알림 폴링 (설정과 무관하게 항상 수신, 독립 cursor) ──
      if (riskPollIntervalRef.current) {
        clearInterval(riskPollIntervalRef.current);
        riskPollIntervalRef.current = null;
      }
      const riskPoll = async () => {
        try {
          const lastPoll = localStorage.getItem(notifRiskPollKey())
            ?? new Date(Date.now() - 60_000).toISOString();
          const now = new Date().toISOString();
          const notifs = await listNotifications(lastPoll);
          localStorage.setItem(notifRiskPollKey(), now);

          for (const n of notifs) {
            if (n.notification_type !== "RISK_CHANGE") continue;
            pushNotification({ category: "위험도", title: "⚠️ 위험도 변화", body: n.message });
            await sendBrowserNotification("⚠️ 위험도 변화", n.message);
          }
        } catch { /* 무시 */ }
      };
      riskPollIntervalRef.current = setInterval(riskPoll, 30_000);

      // ── 강퇴 알림 폴링 (설정과 무관하게 항상 수신, 독립 cursor) ──
      if (kickPollIntervalRef.current) {
        clearInterval(kickPollIntervalRef.current);
        kickPollIntervalRef.current = null;
      }
      const kickPoll = async () => {
        try {
          const lastPoll = localStorage.getItem(notifKickPollKey())
            ?? new Date(Date.now() - 60_000).toISOString();
          const now = new Date().toISOString();
          const notifs = await listNotifications(lastPoll);
          localStorage.setItem(notifKickPollKey(), now);

          for (const n of notifs) {
            if (n.notification_type === "CHALLENGE_KICK") {
              pushNotification({ category: "챌린지", title: "⛔ 챌린지 탈퇴", body: n.message });
              await sendBrowserNotification("⛔ 챌린지 탈퇴", n.message);
            } else if (n.notification_type === "CHALLENGE_INVITE") {
              pushNotification({ category: "챌린지", title: "📩 챌린지 초대", body: n.message });
              await sendBrowserNotification("📩 챌린지 초대", n.message);
            } else if (n.notification_type === "CHALLENGE_DELETE") {
              pushNotification({ category: "챌린지", title: "🗑️ 챌린지 삭제", body: n.message });
              await sendBrowserNotification("🗑️ 챌린지 삭제", n.message);
            }
          }
        } catch { /* 무시 */ }
      };
      kickPollIntervalRef.current = setInterval(kickPoll, 10_000);

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

    scheduleAllRef.current = scheduleAll;
    scheduleAll();

    // 같은 탭 내 변경 감지 — 커스텀 이벤트 (storage 이벤트는 타 탭에서만 발생)
    const handleReschedule = () => scheduleAll();
    window.addEventListener("notif-reschedule", handleReschedule);

    // 다른 탭에서의 변경 감지
    const handleStorage = (e: StorageEvent) => {
      if (e.key === notifSettingsKey() || e.key === MEDICATION_STORAGE_KEY) {
        scheduleAll();
      }
    };
    window.addEventListener("storage", handleStorage);

    return () => {
      localStorage.setItem(notifLastSeenKey(), Date.now().toString());
      timers.forEach(clearTimeout);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (kickPollIntervalRef.current) clearInterval(kickPollIntervalRef.current);
      if (riskPollIntervalRef.current) clearInterval(riskPollIntervalRef.current);
      window.removeEventListener("notif-reschedule", handleReschedule);
      window.removeEventListener("storage", handleStorage);
    };
    // isAuthenticated 가 true 로 바뀌면(로그인) effect 가 다시 실행되며 소급 복구 + 폴링을
    // 셋업하고, false 로 바뀌면(로그아웃) 위 cleanup 으로 폴링 타이머를 정리한다.
  }, [isAuthenticated]);
}
