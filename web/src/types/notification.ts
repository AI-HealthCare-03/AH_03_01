export type NotificationType = "COMMENT" | "REPLY" | "LIKE" | "CHALLENGE_KICK" | "CHALLENGE_INVITE";

export interface Notification {
  id: number;
  notification_type: NotificationType;
  target_type: "POST" | "COMMENT" | "VERIFICATION" | "CHALLENGE";
  target_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
  actor_nickname: string | null;
}
