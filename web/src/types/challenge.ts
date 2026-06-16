/* =========================================
   챌린지 도메인 타입 정의
   백엔드 FastAPI /api/v1/ 엔드포인트 기반
   ========================================= */

import type { ChallengeCategory } from "./api";

export type { ChallengeCategory };

/* 챌린지 범위 */
export type ChallengeScope = "PERSONAL" | "GROUP";

/* 챌린지 공개 설정 */
export type ChallengeVisibility = "PUBLIC" | "PRIVATE";

/* 챌린지 상태 */
export type ChallengeStatus =
  | "RECRUITING"
  | "ACTIVE"
  | "COMPLETED"
  | "CANCELLED";

/* 목표 타입 */
export type GoalType = "DURATION" | "COUNT" | "AMOUNT" | "CHECK";

/* 운동 서브타입 */
export type ExerciseSubType =
  | "WALKING"
  | "RUNNING"
  | "STRENGTH"
  | "CYCLING"
  | "SWIMMING"
  | "OTHER";

/* 인증 방식 */
export type VerificationMethod = "CHECK" | "PHOTO" | "SHIELD";

/* 참여자 상태 */
export type ParticipantStatus = "PENDING" | "APPROVED" | "REJECTED" | "LEFT";

/* 인증 상태 */
export type VerificationStatus = "PENDING" | "APPROVED" | "REJECTED";

/* 반응 타입 */
export type ReactionType = "LIKE" | "COMMENT";

/* ─── 챌린지 ─── */
export interface Challenge {
  id: number;
  title: string;
  description?: string | null;
  category: ChallengeCategory;
  sub_category?: ExerciseSubType | null;
  scope: ChallengeScope;
  status: ChallengeStatus;
  goal_type: GoalType;
  goal_value: number;
  start_date: string;
  end_date: string;
  max_participants?: number | null;
  verification_type: VerificationMethod;
  invite_code?: string | null;
  visibility?: ChallengeVisibility | null;
  is_member?: boolean;
  created_by?: number;
  creator_id?: string | null;  /* UUID — 상세 API에서 제공 */
  created_at: string;
  /* 신규: cadence + goal_config */
  cadence?: ChallengeCadence | null;
  goal_config?: ChallengeGoalConfig | null;
  /* 클라이언트 계산 필드 (API에 없을 수 있음) */
  participant_count?: number;
  my_progress?: number;      /* 내 달성일 수 */
  total_days?: number;       /* 전체 기간 일 수 */
  achievement_rate?: number; /* 달성률 % (그룹: 전체 멤버 기준, 개인: 내 기준) */
  missed_count?: number;     /* 누락 횟수 */
  my_participant_status?: ParticipantStatus | null;  /* 내 참여 상태 (mine 쿼리 시) */
}

/* 챌린지 목록 응답 */
export interface ChallengeListResponse {
  items: Challenge[];
  total_elements: number;
  total_pages: number;
  page: number;
  size: number;
}

/* 챌린지 생성 요청 */
export interface CreateChallengeRequest {
  title: string;
  description?: string;
  category: ChallengeCategory;
  sub_category?: ExerciseSubType;
  scope: ChallengeScope;
  goal_type: GoalType;
  goal_value: number;
  start_date: string;
  end_date: string;
  max_participants?: number;
  verification_type: VerificationMethod;
  /* 신규 옵션 필드 */
  cadence?: ChallengeCadence;
  goal_config?: ChallengeGoalConfig;
  visibility?: ChallengeVisibility;
}

/* 챌린지 수정 요청 */
export type UpdateChallengeRequest = Partial<CreateChallengeRequest> & { status?: ChallengeStatus };

/* ─── 참여자 ─── */
export interface ChallengeParticipant {
  id: number;
  user_id: string; /* UUID */
  challenge_id: number;
  role?: "OWNER" | "MEMBER";
  status: ParticipantStatus;
  joined_at: string;
  progress_days?: number;
  achievement_rate?: number; /* 개인 달성률 % */
  missed_count?: number;
  user?: {
    id: string; /* UUID */
    name: string;
    nickname?: string | null;
  };
}

export interface ParticipantListResponse {
  items: ChallengeParticipant[];
  total: number;
}

/* ─── 인증 ─── */
export interface ChallengeVerification {
  id: number;
  challenge_id: number;
  user_id: string; /* UUID */
  method: VerificationMethod;
  status: VerificationStatus;
  checked?: boolean | null;
  photo_file_id?: number | null;
  shield_inventory_id?: number | null;
  memo?: string | null;
  /* REJECTED 시 SigLIP2 판정 사유(점수/임계값) */
  rejection_reason?: string | null;
  verified_date?: string | null;  /* YYYY-MM-DD, 백엔드 verified_date */
  verified_at?: string | null;
  created_at: string;
  earned_points?: number | null;  /* APPROVED 인증 시 실제 적립 포인트 */
}

export interface CreateVerificationRequest {
  challenge_id: number;
  method: VerificationMethod;
  /* YYYY-MM-DD. 백엔드 DTO 가 필수로 요구. */
  verified_date: string;
  checked?: boolean;
  photo_file_id?: number;
  shield_inventory_id?: number;
  caption?: string;
  duration_seconds?: number;
  /* 설문형 인증 응답 (예: 당뇨발 9문항 → {template, wound, blister, ...}) */
  answers?: Record<string, string>;
}

export interface VerificationListResponse {
  items: ChallengeVerification[];
  total: number;
}

/* ─── 반응 ─── */
export interface VerificationReaction {
  id: number;
  verification_id: number;
  user_id: string; /* UUID */
  type: ReactionType;
  content?: string | null;
  created_at: string;
  user?: {
    id: string; /* UUID */
    name: string;
    nickname?: string | null;
  };
}

export interface CreateReactionRequest {
  type: ReactionType;
  content?: string;
}

export interface ReactionWithReplies extends VerificationReaction {
  replies: VerificationReaction[];
}

export interface ReactionListResponse {
  like_count: number;
  my_like: boolean;
  comments: ReactionWithReplies[];
}

/* ─── 요약 ─── */
export interface ChallengeSummaryItem {
  challenge_id: number;
  title: string;
  category: ChallengeCategory;
  total_days: number;
  completed_days: number;
  success_rate: number;
  earned_points: number;
}

export interface ChallengeSummaryResponse {
  period: "weekly" | "monthly";
  average_success_rate: number;
  total_earned_points: number;
  items: ChallengeSummaryItem[];
}

/* ─── cadence 타입 ─── */
export type ChallengeCadence =
  | "DAILY"
  | "WEEKLY_COUNT"
  | "GROUP_SUM"
  | "GROUP_MEMBERS";

/* ─── goal_config 구조 ─── */
export interface ChallengeGoalConfig {
  /* 공통 */
  amount?: { value: number; unit: string };
  duration_minutes?: number;
  distance_km?: number;
  step_count?: number;
  weekly_target_count?: number;
  group_target_count?: number;
  group_target_members?: number;
  /* 수면 */
  sleep_mode?: "BED_TIME" | "SLEEP_DURATION" | "WAKE_TIME";
  sleep_time_range?: string;       /* "22-23" 형식 */
  sleep_duration_hours?: number;
  wake_time?: string;              /* "07:00" 형식 */
  /* 식단 */
  diet_mode?: "AVOID" | "INCLUDE";
  diet_targets?: string[];
  diet_type?: "MEDITERRANEAN" | "LOW_CARB" | "LOW_FAT" | "LOW_SODIUM" | "LOW_SUGAR";
  /* 체중 */
  weight_loss_mode?: "MAINTAIN" | "USER_INPUT" | "PERCENT_5";
  weight_loss_kg?: number;
  /* 운동 기타 */
  exercise_other_type?: string;
  /* 질환 관리 */
  questionnaire_template?: string;
  /* 보조 분류 */
  kind?: "WEIGHT";
}

/* ─── 피드 ─── */
export interface VerificationFeedItem {
  id: number;
  user_id: string;
  user_nickname: string | null;
  method: VerificationMethod;
  verified_date: string;
  caption: string | null;
  photo_file_id: number | null;
  verified_duration_seconds: number | null;
  like_count: number;
  comment_count: number;
  my_like: boolean;
  created_at: string;
  status: VerificationStatus;
}

export interface VerificationFeedResponse {
  page: number;
  size: number;
  total_elements: number;
  total_pages: number;
  items: VerificationFeedItem[];
}

/* ─── 위저드 폼 상태 ─── */
export interface WizardFormState {
  scope: ChallengeScope;
  visibility: ChallengeVisibility;
  category: ChallengeCategory | null;
  sub_category: ExerciseSubType | null;
  /* Step3 내 세부 모드 분기 */
  step3Mode: string | null; /* "DAILY" | "WEEKLY_COUNT" | BED_TIME | AVOID | DIABETIC_FOOT | WALKING ... */
  goal_type: GoalType;
  goal_value: number;
  duration_days: 7 | 14 | 30 | 90 | 180; /* WEIGHT_MANAGEMENT 는 90/180 까지 */
  title: string;
  max_participants: number;
  verification_type: VerificationMethod;
  /* 신규 필드 */
  cadence: ChallengeCadence | null;
  goal_config: ChallengeGoalConfig;
}
