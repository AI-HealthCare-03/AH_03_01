/* =========================================
   챌린지 도메인 타입 정의
   백엔드 FastAPI /api/v1/ 엔드포인트 기반
   ========================================= */

import type { ChallengeCategory } from "./api";

export type { ChallengeCategory };

/* 챌린지 범위 */
export type ChallengeScope = "PERSONAL" | "GROUP";

/* 챌린지 상태 */
export type ChallengeStatus =
  | "ACTIVE"
  | "COMPLETED"
  | "CANCELLED"
  | "RECRUITING";

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
  created_by: number;
  created_at: string;
  /* 클라이언트 계산 필드 (API에 없을 수 있음) */
  participant_count?: number;
  my_progress?: number;      /* 내 달성일 수 */
  total_days?: number;       /* 전체 기간 일 수 */
  missed_count?: number;     /* 누락 횟수 */
}

/* 챌린지 목록 응답 */
export interface ChallengeListResponse {
  items: Challenge[];
  total: number;
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
}

/* 챌린지 수정 요청 */
export type UpdateChallengeRequest = Partial<CreateChallengeRequest>;

/* ─── 참여자 ─── */
export interface ChallengeParticipant {
  id: number;
  user_id: number;
  challenge_id: number;
  status: ParticipantStatus;
  joined_at: string;
  progress_days?: number;
  missed_count?: number;
  user?: {
    id: number;
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
  user_id: number;
  method: VerificationMethod;
  status: VerificationStatus;
  checked?: boolean | null;
  photo_file_id?: number | null;
  shield_inventory_id?: number | null;
  memo?: string | null;
  verified_at?: string | null;
  created_at: string;
}

export interface CreateVerificationRequest {
  challenge_id: number;
  method: VerificationMethod;
  checked?: boolean;
  photo_file_id?: number;
  shield_inventory_id?: number;
  memo?: string;
}

export interface VerificationListResponse {
  items: ChallengeVerification[];
  total: number;
}

/* ─── 반응 ─── */
export interface VerificationReaction {
  id: number;
  verification_id: number;
  user_id: number;
  type: ReactionType;
  content?: string | null;
  created_at: string;
  user?: {
    id: number;
    name: string;
    nickname?: string | null;
  };
}

export interface CreateReactionRequest {
  type: ReactionType;
  content?: string;
}

export interface ReactionListResponse {
  items: VerificationReaction[];
  total: number;
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

/* ─── 위저드 폼 상태 ─── */
export interface WizardFormState {
  scope: ChallengeScope;
  category: ChallengeCategory | null;
  sub_category: ExerciseSubType | null;
  goal_type: GoalType;
  goal_value: number;
  duration_days: 7 | 14 | 30;
  title: string;
  max_participants: number;
  verification_type: VerificationMethod;
}
