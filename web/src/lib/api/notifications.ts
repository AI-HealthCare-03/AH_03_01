import apiClient from "./client";
import type { Notification } from "@/types/notification";

export async function listNotifications(since?: string): Promise<Notification[]> {
  const res = await apiClient.get<Notification[]>("/api/v1/notifications", {
    params: since ? { since } : {},
  });
  return res.data;
}

export async function markRead(id: number): Promise<void> {
  await apiClient.patch(`/api/v1/notifications/${id}/read`);
}

export async function markAllRead(): Promise<void> {
  await apiClient.patch("/api/v1/notifications/read-all");
}
