/* =========================================
   챌린지 도메인 API 함수
   /api/v1/ prefix 기반 apiClient 사용
   ========================================= */

import apiClient from "./client";
import type {
  Challenge,
  ChallengeListResponse,
  CreateChallengeRequest,
  UpdateChallengeRequest,
  ChallengeParticipant,
  ParticipantListResponse,
  ChallengeVerification,
  CreateVerificationRequest,
  VerificationListResponse,
  VerificationReaction,
  CreateReactionRequest,
  ReactionListResponse,
  ChallengeSummaryResponse,
} from "@/types/challenge";
import type { ChallengeStatus, ChallengeScope } from "@/types/challenge";

/* ─── 챌린지 목록 ─── */
export async function fetchChallenges(params: {
  mine?: boolean;
  status?: ChallengeStatus;
  scope?: ChallengeScope;
  inviteCode?: string;
  size?: number;
  page?: number;
}): Promise<ChallengeListResponse> {
  const { data } = await apiClient.get<ChallengeListResponse>(
    "/api/v1/challenges",
    { params }
  );
  return data;
}

/* ─── 챌린지 단건 ─── */
export async function fetchChallenge(id: number): Promise<Challenge> {
  const { data } = await apiClient.get<Challenge>(`/api/v1/challenges/${id}`);
  return data;
}

/* ─── 챌린지 생성 ─── */
export async function createChallenge(
  body: CreateChallengeRequest
): Promise<Challenge> {
  const { data } = await apiClient.post<Challenge>("/api/v1/challenges", body);
  return data;
}

/* ─── 챌린지 수정 ─── */
export async function updateChallenge(
  id: number,
  body: UpdateChallengeRequest
): Promise<Challenge> {
  const { data } = await apiClient.patch<Challenge>(
    `/api/v1/challenges/${id}`,
    body
  );
  return data;
}

/* ─── 챌린지 삭제 ─── */
export async function deleteChallenge(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/challenges/${id}`);
}

/* ─── 참여자 목록 ─── */
export async function fetchParticipants(
  challengeId: number
): Promise<ParticipantListResponse> {
  const { data } = await apiClient.get<ParticipantListResponse>(
    `/api/v1/challenges/${challengeId}/participants`
  );
  return data;
}

/* ─── 챌린지 참가 (코드 참가) ─── */
export async function joinChallenge(
  challengeId: number,
  inviteCode?: string
): Promise<ChallengeParticipant> {
  const { data } = await apiClient.post<ChallengeParticipant>(
    `/api/v1/challenges/${challengeId}/participants`,
    inviteCode ? { invite_code: inviteCode } : {},
    { params: { action: "join" } }
  );
  return data;
}

/* ─── 챌린지 탈퇴 ─── */
export async function leaveChallenge(challengeId: number): Promise<void> {
  await apiClient.delete(`/api/v1/challenges/${challengeId}/participants`);
}

/* ─── 코드만으로 챌린지 참가 (코드 입력형) ─── */
export interface JoinByCodeResponse {
  challenge_id: number;
  status: string;
}
export async function joinChallengeByCode(inviteCode: string): Promise<JoinByCodeResponse> {
  const { data } = await apiClient.post<JoinByCodeResponse>(
    "/api/v1/challenges/join-by-code",
    { invite_code: inviteCode },
  );
  return data;
}

/* ─── 사용자 닉네임 검색 (초대 대상 찾기) ─── */
export interface UserSearchItem {
  id: string; /* UUID */
  name: string;
}
export async function searchUsersByNickname(
  nickname: string,
  limit = 10,
): Promise<UserSearchItem[]> {
  const { data } = await apiClient.get<{ items: UserSearchItem[] }>(
    "/api/v1/users/search",
    { params: { nickname, limit } },
  );
  return data.items;
}

/* ─── 받은 직접 초대 목록 + 응답 ─── */
export interface MyInvitationItem {
  id: number;
  challenge_id: number;
  challenge_title: string | null;
  challenge_category: string | null;
  inviter_id: string | null;
  inviter_name: string | null;
  status: "PENDING" | "ACCEPTED" | "REJECTED" | "EXPIRED";
  expires_at: string | null;
  created_at: string;
}
export async function fetchMyInvitations(statusFilter?: string): Promise<MyInvitationItem[]> {
  const { data } = await apiClient.get<{ items: MyInvitationItem[] }>(
    "/api/v1/challenge-invitations",
    { params: statusFilter ? { status: statusFilter } : {} },
  );
  return data.items;
}
export async function respondToInvitation(
  invitationId: number,
  action: "accept" | "reject",
): Promise<{ id: number; status: string }> {
  const { data } = await apiClient.patch<{ id: number; status: string }>(
    `/api/v1/challenge-invitations/${invitationId}`,
    null,
    { params: { action } },
  );
  return data;
}

/* ─── PENDING 참가 신청 처리 (방장이 수락/거절) ─── */
export async function respondToPendingParticipant(
  challengeId: number,
  targetUserId: string,
  action: "approve" | "reject",
  reason?: string,
): Promise<{ user_id: string; status: string }> {
  const { data } = await apiClient.patch<{ user_id: string; status: string }>(
    `/api/v1/challenges/${challengeId}/participants/${targetUserId}`,
    null,
    { params: reason ? { action, reason } : { action } },
  );
  return data;
}

/* ─── 사용자에게 직접 초대 발송 ─── */
export interface DirectInviteResponse {
  invite_id: number;
  invite_code: string;
  expires_at: string;
}
export async function inviteUserToChallenge(
  challengeId: number,
  inviteeId: string, /* UUID */
): Promise<DirectInviteResponse> {
  const { data } = await apiClient.post<DirectInviteResponse>(
    `/api/v1/challenges/${challengeId}/participants`,
    { invitee_id: inviteeId },
    { params: { action: "invite" } },
  );
  return data;
}

/* ─── 방장 참여자 승인/거절 ─── */
export async function approveParticipant(
  challengeId: number,
  userId: number,
  action: "approve" | "reject"
): Promise<ChallengeParticipant> {
  const { data } = await apiClient.patch<ChallengeParticipant>(
    `/api/v1/challenges/${challengeId}/participants/${userId}`,
    {},
    { params: { action } }
  );
  return data;
}

/* ─── 인증 생성 ─── */
export async function createVerification(
  body: CreateVerificationRequest,
  method: "CHECK" | "PHOTO" | "SHIELD"
): Promise<ChallengeVerification> {
  const { data } = await apiClient.post<ChallengeVerification>(
    "/api/v1/challenge-verifications",
    body,
    { params: { method } }
  );
  return data;
}

/* ─── 인증 목록 ─── */
export async function fetchVerifications(
  challengeId: number
): Promise<VerificationListResponse> {
  const { data } = await apiClient.get<VerificationListResponse>(
    "/api/v1/challenge-verifications",
    { params: { challengeId } }
  );
  return data;
}

/* ─── 인증 단건 ─── */
export async function fetchVerification(
  id: number
): Promise<ChallengeVerification> {
  const { data } = await apiClient.get<ChallengeVerification>(
    `/api/v1/challenge-verifications/${id}`
  );
  return data;
}

/* ─── 인증 반응 목록 ─── */
export async function fetchVerificationReactions(
  verificationId: number
): Promise<ReactionListResponse> {
  const { data } = await apiClient.get<ReactionListResponse>(
    `/api/v1/challenge-verifications/${verificationId}/reactions`
  );
  return data;
}

/* ─── 인증 반응 생성 ─── */
export async function createReaction(
  verificationId: number,
  body: CreateReactionRequest
): Promise<VerificationReaction> {
  const { data } = await apiClient.post<VerificationReaction>(
    `/api/v1/challenge-verifications/${verificationId}/reactions`,
    body
  );
  return data;
}

/* ─── 챌린지 요약 ─── */
export async function fetchChallengeSummary(
  period: "weekly" | "monthly"
): Promise<ChallengeSummaryResponse> {
  const { data } = await apiClient.get<ChallengeSummaryResponse>(
    "/api/v1/challenge-summaries",
    { params: { period } }
  );
  return data;
}

/* ─── 카테고리 목록 ─── */
export async function fetchChallengeCategories(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>(
    "/api/v1/challenge-categories"
  );
  return data;
}
