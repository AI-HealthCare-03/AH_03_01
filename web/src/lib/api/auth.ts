import apiClient from "./client";
import type { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from "@/types";

/* =========================================
   인증 API 래퍼
   백엔드: FastAPI /api/v1/auth/*
   ========================================= */

/**
 * 로그인
 * POST /api/v1/auth/login
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>("/api/v1/auth/login", data);
  return res.data;
}

/**
 * 회원가입
 * POST /api/v1/auth/signup
 * nickname 필드는 백엔드 미지원 — 호출 시 제외
 */
export async function signup(data: SignupRequest): Promise<SignupResponse> {
  const res = await apiClient.post<SignupResponse>("/api/v1/auth/signup", data);
  return res.data;
}

/**
 * 토큰 갱신 (스텁)
 * POST /api/v1/auth/token
 * TODO(backend): refresh_token 응답 추가 후 실제 갱신 로직 연결
 */
export async function refreshToken(): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>("/api/v1/auth/token");
  return res.data;
}

/**
 * 이메일 중복 확인
 * GET /api/v1/auth/check-email?email=...
 */
export async function checkEmailAvailable(
  email: string
): Promise<{ email: string; available: boolean }> {
  const res = await apiClient.get<{ email: string; available: boolean }>(
    "/api/v1/auth/check-email",
    { params: { email } }
  );
  return res.data;
}

/**
 * 닉네임 중복 확인
 * GET /api/v1/auth/check-nickname?nickname=...
 * NOTE: 현 User 모델에 nickname 컬럼 없어 백엔드가 항상 available=true 반환.
 */
export async function checkNicknameAvailable(
  nickname: string
): Promise<{ nickname: string; available: boolean }> {
  const res = await apiClient.get<{ nickname: string; available: boolean }>(
    "/api/v1/auth/check-nickname",
    { params: { nickname } }
  );
  return res.data;
}

/**
 * 아이디 찾기
 * POST /api/v1/auth/find-id
 * 이메일은 서버에서 마스킹되어 반환됨 (j*****3@gmail.com)
 */
export async function findId(
  name: string,
  phone_number: string
): Promise<{ maskedEmail: string; createdAt: string }> {
  const res = await apiClient.post<{ masked_email: string; created_at: string }>(
    "/api/v1/auth/find-id",
    { name, phone_number }
  );
  return { maskedEmail: res.data.masked_email, createdAt: res.data.created_at };
}

/**
 * 이메일 본인 인증 메일 발송
 * POST /api/v1/auth/email/send-verification
 */
export async function sendEmailVerification(email: string): Promise<void> {
  await apiClient.post("/api/v1/auth/email/send-verification", { email });
}

/**
 * 이메일 인증 완료 여부 조회
 * GET /api/v1/auth/email/verification-status?email=...
 */
export async function checkEmailVerified(email: string): Promise<boolean> {
  const res = await apiClient.get<{ email: string; verified: boolean }>(
    "/api/v1/auth/email/verification-status",
    { params: { email } }
  );
  return res.data.verified;
}

/**
 * 비밀번호 재설정 메일 발송
 * TODO(backend): /api/v1/auth/reset-password 엔드포인트 추가 필요
 */
export async function requestPasswordReset(
  _email: string,
  _phone_number: string
): Promise<void> {
  throw new Error(
    "TODO(backend): /api/v1/auth/reset-password 엔드포인트 추가 필요"
  );
}

/**
 * SMS 인증번호 발송
 * TODO(backend): /api/v1/auth/sms/send 엔드포인트 추가 필요
 */
export async function sendSms(_phone_number: string): Promise<void> {
  throw new Error("TODO(backend): /api/v1/auth/sms/send 엔드포인트 추가 필요");
}

/**
 * SMS 인증번호 확인
 * TODO(backend): /api/v1/auth/sms/verify 엔드포인트 추가 필요
 */
export async function verifySms(
  _phone_number: string,
  _code: string
): Promise<void> {
  throw new Error(
    "TODO(backend): /api/v1/auth/sms/verify 엔드포인트 추가 필요"
  );
}

/**
 * 이전 계정 조회
 * TODO(backend): /api/v1/auth/previous-account 엔드포인트 추가 필요
 */
export async function getPreviousAccount(
  _email: string
): Promise<import("@/types").PreviousAccount | null> {
  throw new Error(
    "TODO(backend): /api/v1/auth/previous-account 엔드포인트 추가 필요"
  );
}

/**
 * 이전 계정 복원
 * TODO(backend): /api/v1/auth/restore 엔드포인트 추가 필요
 */
export async function restoreAccount(
  _email: string,
  _keys: string[]
): Promise<void> {
  throw new Error(
    "TODO(backend): /api/v1/auth/restore 엔드포인트 추가 필요"
  );
}

/**
 * 회원탈퇴
 * TODO(backend): /api/v1/users/me 엔드포인트 DELETE 확인 필요
 */
export async function deleteAccount(_reason: string): Promise<void> {
  await apiClient.delete("/api/v1/users/me");
}
