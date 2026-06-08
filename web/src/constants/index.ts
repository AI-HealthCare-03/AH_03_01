/* =========================================
   상수 정의
   ========================================= */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const TOKEN_KEY = "hr_access_token";

export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  SIGNUP: "/signup",
  FORGOT_ID: "/forgot-id",
  FORGOT_PASSWORD: "/forgot-password",
  SMS_VERIFY: "/sms-verify",
  ACCOUNT_RESTORE: "/account-restore",
} as const;

/* 로그인 실패 잠금 임계값 */
export const MAX_LOGIN_ATTEMPTS = 5;

/* SMS 인증 타이머 (초) */
export const SMS_TIMEOUT_SEC = 180;

/* 비밀번호 강도 레이블 */
export const PASSWORD_STRENGTH_LABELS = {
  weak: "약함",
  fair: "보통",
  strong: "강함",
} as const;

/* 회원탈퇴 이유 목록 */
export const WITHDRAWAL_REASONS = [
  "서비스 이용이 불편해요",
  "원하는 기능이 없어요",
  "자주 사용하지 않아요",
  "다른 서비스로 이동할게요",
  "기타",
] as const;

/* 복원 데이터 항목 */
export const RESTORE_DATA_ITEMS = [
  { key: "health" as const, label: "건강 기록 (혈압/혈당/복약)" },
  { key: "challenge" as const, label: "챌린지 기록 및 진행 현황" },
  { key: "points" as const, label: "보유 포인트" },
  { key: "profile" as const, label: "프로필 (닉네임·사진)" },
  { key: "community" as const, label: "커뮤니티 활동 내역" },
] as const;

/* 파괴적 모달 삭제 항목 */
export const DESTRUCT_ITEMS = [
  { label: "건강 데이터", value: "142건" },
  { label: "챌린지 참여", value: "42개" },
  { label: "보유 포인트", value: "2,840 P" },
  { label: "캐릭터", value: "함께" },
  { label: "커뮤니티 활동", value: "글 12 · 댓글 47" },
] as const;
