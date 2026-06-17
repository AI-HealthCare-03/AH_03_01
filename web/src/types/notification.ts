export type NotificationType = "COMMENT" | "REPLY" | "LIKE" | "CHALLENGE_KICK" | "CHALLENGE_INVITE" | "CHALLENGE_DELETE" | "RISK_CHANGE";

export interface Notification {
  id: number;
  notification_type: NotificationType;
  target_type: "POST" | "COMMENT" | "VERIFICATION" | "CHALLENGE" | "DISEASE_RISK";
  target_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
  actor_nickname: string | null;
}
