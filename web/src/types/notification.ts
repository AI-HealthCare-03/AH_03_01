export type NotificationType = "COMMENT" | "REPLY" | "LIKE";

export interface Notification {
  id: number;
  notification_type: NotificationType;
  target_type: "POST" | "COMMENT" | "VERIFICATION";
  target_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
  actor_nickname: string | null;
}
