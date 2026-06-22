import axios from "axios";
import apiClient from "./client";
import type {
  LoginRequest,
  LoginResponse,
  PreviousAccount,
  RestoredAccount,
  SignupRequest,
  SignupResponse,
} from "@/types";

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
): Promise<{ maskedEmail: string | null; socialProvider: string | null; createdAt: string }> {
  const res = await apiClient.post<{
    masked_email: string | null;
    social_provider: string | null;
    created_at: string;
  }>("/api/v1/auth/find-id", { name, phone_number });
  return {
    maskedEmail: res.data.masked_email,
    socialProvider: res.data.social_provider,
    createdAt: res.data.created_at,
  };
}

/**
 * 이메일 본인 인증 메일 발송
 * POST /api/v1/auth/email/send-verification
 */
export async function sendEmailVerification(email: string, name?: string, purpose?: string): Promise<void> {
  // name 을 보내면 백엔드가 email+name 일치 활성 계정에만 메일을 발송한다(비번 찾기 본인확인).
  // 회원가입/계정복구는 name 없이 호출(기존 동작 유지).
  // purpose 를 보내면 인증 완료 플래그가 그 네임스페이스로 격리된다(예: 로그인 상태 비번 변경).
  await apiClient.post("/api/v1/auth/email/send-verification", {
    email,
    ...(name ? { name } : {}),
    ...(purpose ? { purpose } : {}),
  });
}

/**
 * 이메일 인증 토큰 검증 (메일 링크의 /verify-email 페이지에서 호출)
 * POST /api/v1/auth/email/verify
 */
export async function verifyEmailToken(token: string): Promise<string> {
  const res = await apiClient.post<{ email: string; verified: boolean }>(
    "/api/v1/auth/email/verify",
    { token }
  );
  return res.data.email;
}

/**
 * 이메일 인증 완료 여부 조회
 * GET /api/v1/auth/email/verification-status?email=...
 */
export async function checkEmailVerified(email: string, purpose?: string): Promise<boolean> {
  const res = await apiClient.get<{ email: string; verified: boolean }>(
    "/api/v1/auth/email/verification-status",
    { params: { email, ...(purpose ? { purpose } : {}) } }
  );
  return res.data.verified;
}

/**
 * 비밀번호 재설정 (비밀번호 찾기)
 * POST /api/v1/auth/reset-password — 이메일 본인 인증 + email/name 일치 필수.
 * 새 비밀번호가 기존과 같으면 "이미 사용한 번호입니다"(400).
 */
export async function resetPassword(
  email: string,
  name: string,
  new_password: string
): Promise<void> {
  await apiClient.post("/api/v1/auth/reset-password", { email, name, new_password });
}

/**
 * 로그인 잠금 해제
 * POST /api/v1/auth/unlock — 이메일 본인 인증 + email/name 일치 필수.
 * 400: 이메일 인증 미완료 / 404: email+name 불일치
 */
export async function unlockAccount(email: string, name: string): Promise<void> {
  await apiClient.post("/api/v1/auth/unlock", { email, name });
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
 * 이전(탈퇴) 계정 감지
 * GET /api/v1/auth/previous-account?email=...
 * 탈퇴 계정이 없으면(404) null 반환 — 정상 신규 가입 흐름으로 분기한다.
 */
export async function getPreviousAccount(
  email: string
): Promise<PreviousAccount | null> {
  try {
    const res = await apiClient.get<PreviousAccount>(
      "/api/v1/auth/previous-account",
      { params: { email } }
    );
    return res.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) return null;
    throw err;
  }
}

/**
 * 탈퇴 계정 복구 (전체 복원)
 * POST /api/v1/auth/restore — 이메일 본인 인증 필수. 복구 후 상세 통계 반환.
 */
export async function restoreAccount(email: string): Promise<RestoredAccount> {
  const res = await apiClient.post<RestoredAccount>("/api/v1/auth/restore", {
    email,
  });
  return res.data;
}

/**
 * 탈퇴 계정 즉시 영구 파기 ('새로 시작하기')
 * POST /api/v1/auth/destroy — 이메일 본인 인증 필수.
 */
export async function destroyPreviousAccount(email: string): Promise<void> {
  await apiClient.post("/api/v1/auth/destroy", { email });
}

/**
 * 회원탈퇴 (soft delete)
 * DELETE /api/v1/users/me — 탈퇴 이유(reason)는 선택. 30일 보관 후 파기.
 */
export async function deleteAccount(reason: string): Promise<void> {
  await apiClient.delete("/api/v1/users/me", { data: { reason } });
}

/* ── 카카오 OAuth ── */

/**
 * 카카오 로그인 URL 조회
 * GET /api/v1/auth/kakao/authorize-url
 */
export async function getKakaoAuthorizeUrl(): Promise<import("@/types").KakaoAuthorizeUrlResponse> {
  const res = await apiClient.get<import("@/types").KakaoAuthorizeUrlResponse>(
    "/api/v1/auth/kakao/authorize-url"
  );
  return res.data;
}

/**
 * 카카오 콜백 처리
 * POST /api/v1/auth/kakao/callback
 */
export async function kakaoCallback(
  code: string,
  state: string
): Promise<import("@/types").KakaoCallbackResponse> {
  const res = await apiClient.post<import("@/types").KakaoCallbackResponse>(
    "/api/v1/auth/kakao/callback",
    { code, state }
  );
  return res.data;
}

/**
 * 카카오 소셜 회원가입
 * POST /api/v1/auth/kakao/signup
 */
export async function kakaoSignup(
  data: import("@/types").KakaoSignupRequest
): Promise<import("@/types").KakaoSignupResponse> {
  const res = await apiClient.post<import("@/types").KakaoSignupResponse>(
    "/api/v1/auth/kakao/signup",
    data
  );
  return res.data;
}

/**
 * 카카오 탈퇴 계정 복구 (복구 후 바로 로그인)
 * POST /api/v1/auth/kakao/restore
 */
export async function kakaoRestore(
  restoreTicket: string
): Promise<import("@/types").KakaoSignupResponse> {
  const res = await apiClient.post<import("@/types").KakaoSignupResponse>(
    "/api/v1/auth/kakao/restore",
    { restore_ticket: restoreTicket }
  );
  return res.data;
}

/**
 * 카카오 탈퇴 계정 영구 파기 ('새로 시작하기')
 * POST /api/v1/auth/kakao/destroy
 */
export async function kakaoDestroy(restoreTicket: string): Promise<void> {
  await apiClient.post("/api/v1/auth/kakao/destroy", { restore_ticket: restoreTicket });
}
