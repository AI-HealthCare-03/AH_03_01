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
  nickname: string;
  gender: "MALE" | "FEMALE";
  birth_date: string; /* YYYY-MM-DD */
  phone_number: string;
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

/* 이전(탈퇴) 계정 감지 — GET /api/v1/auth/previous-account (인증 전, 마스킹) */
export interface PreviousAccount {
  masked_email: string;
  deleted_at: string;
  restore_deadline: string;
}

/* 복구 완료 응답 — POST /api/v1/auth/restore (이메일 인증 후, 상세 통계) */
export interface RestoredAccount {
  email: string;
  created_at: string;
  deleted_at: string;
  challenge_count: number;
  points: number;
  pet_name?: string;
}

export type RestoreDataKey =
  | "health"
  | "challenge"
  | "points"
  | "profile"
  | "community";

/* 폼 검증 상태 */
export type PasswordStrength = "weak" | "fair" | "strong";

/* ── 카카오 OAuth ── */

/** GET /api/v1/auth/kakao/authorize-url */
export interface KakaoAuthorizeUrlResponse {
  authorize_url: string;
  state: string;
}

/** POST /api/v1/auth/kakao/callback — 기존 회원 로그인 */
export interface KakaoCallbackLoginResponse {
  status: "login";
  access_token: string;
}

/** POST /api/v1/auth/kakao/callback — 신규 회원, 추가 정보 입력 필요 */
export interface KakaoCallbackSignupRequiredResponse {
  status: "signup_required";
  signup_ticket: string;
  prefill: {
    nickname: string | null;
    email: string | null;
  };
}

/** POST /api/v1/auth/kakao/callback — 탈퇴 계정 발견, 복구/파기 선택 필요 */
export interface KakaoCallbackRestoreRequiredResponse {
  status: "restore_required";
  restore_ticket: string;
  masked_email: string;
  deleted_at: string;
  restore_deadline: string;
}

export type KakaoCallbackResponse =
  | KakaoCallbackLoginResponse
  | KakaoCallbackSignupRequiredResponse
  | KakaoCallbackRestoreRequiredResponse;

/** POST /api/v1/auth/kakao/signup */
export interface KakaoSignupRequest {
  signup_ticket: string;
  email: string;
  name: string;
  nickname: string;
  gender: "MALE" | "FEMALE";
  birth_date: string; /* YYYY-MM-DD */
  phone_number: string;
  terms_agreed: boolean;
  privacy_agreed: boolean;
}

export interface KakaoSignupResponse {
  access_token: string;
}
