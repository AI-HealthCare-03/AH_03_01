import { ACTIVE_USER_KEY } from "@/stores/auth";

export function activeUserId(): string {
  return (typeof window !== "undefined" && localStorage.getItem(ACTIVE_USER_KEY)) || "guest";
}

export const notifHistoryKey    = () => `notification-history:${activeUserId()}`;
export const notifLastSeenKey   = () => `notif-last-seen:${activeUserId()}`;
export const notifSettingsKey   = () => `notification-settings:${activeUserId()}`;
export const notifSocialPollKey = () => `notification-social-poll:${activeUserId()}`;
export const notifKickPollKey   = () => `notification-kick-poll:${activeUserId()}`;
export const notifRiskPollKey   = () => `notification-risk-poll:${activeUserId()}`;
export const riskLevelCacheKey  = () => `risk-level-cache:${activeUserId()}`;
export const medSnapshotKey     = (date: string) => `med-snapshot-${date}:${activeUserId()}`;

/** 알림 내역에서 id에 해당하는 항목의 checked 값을 갱신하고 notif-updated 이벤트를 발송. 실패 시 throw. */
export function updateNotifChecked(id: string, checked: boolean): void {
  const raw = localStorage.getItem(notifHistoryKey());
  const list = raw ? (JSON.parse(raw) as Array<Record<string, unknown>>) : [];
  const next = list.map((n) => n["id"] === id ? { ...n, checked, read: true } : n);
  localStorage.setItem(notifHistoryKey(), JSON.stringify(next));
  window.dispatchEvent(new CustomEvent("notif-updated"));
}
