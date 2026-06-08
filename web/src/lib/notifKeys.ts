import { ACTIVE_USER_KEY } from "@/stores/auth";

export function activeUserId(): string {
  return (typeof window !== "undefined" && localStorage.getItem(ACTIVE_USER_KEY)) || "guest";
}

export const notifHistoryKey  = () => `notification-history:${activeUserId()}`;
export const notifLastSeenKey = () => `notif-last-seen:${activeUserId()}`;
export const notifSettingsKey = () => `notification-settings:${activeUserId()}`;
