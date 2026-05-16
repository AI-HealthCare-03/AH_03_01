/* =========================================
   공통 타입 정의
   ========================================= */

/* API 에러 응답 */
export interface ApiError {
  detail: string | ValidationErrorDetail[];
}

export interface ValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/* 인증 */
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  name: string;
  gender: "MALE" | "FEMALE";
  birth_date: string; /* YYYY-MM-DD */
  phone_number: string;
  /* nickname: string; // TODO(backend): nickname 필드 추가 후 연결 */
}

export interface SignupResponse {
  detail: string;
}

/* 사용자 */
export interface User {
  id: number;
  email: string;
  name: string;
  nickname?: string;
  gender: "MALE" | "FEMALE";
  birth_date: string;
  phone_number: string;
  created_at: string;
}

/* 이전 계정 (복원) */
export interface PreviousAccount {
  email: string;
  created_at: string;
  deleted_at: string;
  challenge_count: number;
  points: number;
  pet_name?: string;
  restore_deadline: string;
}

export type RestoreDataKey =
  | "health"
  | "challenge"
  | "points"
  | "profile"
  | "community";

/* 폼 검증 상태 */
export type PasswordStrength = "weak" | "fair" | "strong";
