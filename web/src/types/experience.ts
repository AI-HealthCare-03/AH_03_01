/* =========================================
   주간 활동량(EXP) + 리더보드 타입
   ========================================= */

export type XpKind =
  | "HEALTH_INPUT"
  | "HEALTH_VIEW"
  | "CHALLENGE_VERIFY"
  | "POST"
  | "COMMENT"
  | "QUIZ";

export interface WeeklyXpBreakdownItem {
  kind: XpKind;
  count: number;
  points: number;
}

export interface WeeklyXpResponse {
  week_id: string; // "2026-W20"
  total_points: number;
  items: WeeklyXpBreakdownItem[];
}

export interface LeaderboardEntry {
  user_id: string; /* UUID */
  user_name: string;
  points: number;
  rank: number;
}

export interface LeaderboardResponse {
  week_id: string;
  entries: LeaderboardEntry[];
  my_rank: number | null;
  my_points: number;
}
