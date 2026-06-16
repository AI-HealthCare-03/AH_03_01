import apiClient from "./client";

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_challenges: number;
  active_challenges: number;
  total_posts: number;
  pending_inquiries: number;
  pending_reports: number;
}

export interface AdminUserItem {
  id: string;
  email: string;
  name: string;
  nickname: string | null;
  created_at: string;
  last_login: string | null;
  is_active: boolean;
  is_banned: boolean;
  ban_reason: string | null;
  report_count: number;
}

export interface AdminUserDetail extends AdminUserItem {
  phone_number: string;
  post_count: number;
  comment_count: number;
}

export interface AdminChallengeItem {
  id: number;
  title: string;
  scope: string;
  status: string;
  category: string;
  participant_count: number;
  start_date: string;
  end_date: string;
  created_at: string;
}

export interface AdminReportItem {
  id: number;
  target_type: string;
  target_id: number;
  reason: string;
  reporter_id: string;
  created_at: string;
  /* 신고된 게시글/댓글의 작성자·내용 (POST/COMMENT 만 채워짐) */
  author_nickname?: string | null;
  author_name?: string | null;
  content_preview?: string | null;
  target_exists?: boolean;
}

export interface AdminInquiryItem {
  id: number;
  user_email: string;
  title: string;
  category: string;
  status: string;
  created_at: string;
}

export interface FAQItem {
  id: number;
  question: string;
  answer: string;
  category: string;
  order: number;
  is_deleted?: boolean;
}

export interface AdminNoticeItem {
  id: number;
  title: string;
  content: string;
  created_at: string;
  author_name: string | null;
  is_deleted?: boolean;
}

const BASE = "/api/v1/admin";

export const adminApi = {
  getStats: () =>
    apiClient.get<AdminStats>(`${BASE}/stats`).then((r) => r.data),

  // 회원
  listUsers: (params?: { offset?: number; limit?: number; search?: string }) =>
    apiClient.get<AdminUserItem[]>(`${BASE}/users`, { params }).then((r) => r.data),
  getUser: (id: string) =>
    apiClient.get<AdminUserDetail>(`${BASE}/users/${id}`).then((r) => r.data),
  banUser: (id: string, reason: string) =>
    apiClient.post(`${BASE}/users/${id}/ban`, { reason }),
  unbanUser: (id: string) =>
    apiClient.delete(`${BASE}/users/${id}/ban`),

  // 챌린지
  listChallenges: (params?: { offset?: number; limit?: number; status?: string }) =>
    apiClient.get<AdminChallengeItem[]>(`${BASE}/challenges`, { params }).then((r) => r.data),

  // 신고
  listReports: (params?: { offset?: number; limit?: number }) =>
    apiClient.get<AdminReportItem[]>(`${BASE}/reports`, { params }).then((r) => r.data),
  dismissReport: (id: number) =>
    apiClient.delete(`${BASE}/reports/${id}`),
  deletePost: (id: number) =>
    apiClient.delete(`${BASE}/community/posts/${id}`),
  deleteComment: (id: number) =>
    apiClient.delete(`${BASE}/community/comments/${id}`),

  // 문의
  listInquiries: (params?: { offset?: number; limit?: number; status?: string }) =>
    apiClient.get<AdminInquiryItem[]>(`${BASE}/inquiries`, { params }).then((r) => r.data),
  answerInquiry: (id: number, content: string) =>
    apiClient.post(`${BASE}/inquiries/${id}/answer`, { content }),

  // FAQ
  listFaqs: (params?: { show_deleted?: boolean }) =>
    apiClient.get<FAQItem[]>(`${BASE}/faqs`, { params }).then((r) => r.data),
  createFaq: (data: { question: string; answer: string; category: string; order: number }) =>
    apiClient.post<FAQItem>(`${BASE}/faqs`, data).then((r) => r.data),
  updateFaq: (id: number, data: Partial<{ question: string; answer: string; category: string; order: number }>) =>
    apiClient.patch<FAQItem>(`${BASE}/faqs/${id}`, data).then((r) => r.data),
  deleteFaq: (id: number) =>
    apiClient.delete(`${BASE}/faqs/${id}`),

  // 공지사항
  listNotices: (params?: { offset?: number; limit?: number; show_deleted?: boolean }) =>
    apiClient.get<AdminNoticeItem[]>(`${BASE}/notices`, { params }).then((r) => r.data),
  createNotice: (data: { title: string; content: string }) =>
    apiClient.post<AdminNoticeItem>(`${BASE}/notices`, data).then((r) => r.data),
  updateNotice: (id: number, data: Partial<{ title: string; content: string }>) =>
    apiClient.patch<AdminNoticeItem>(`${BASE}/notices/${id}`, data).then((r) => r.data),
  deleteNotice: (id: number) =>
    apiClient.delete(`${BASE}/notices/${id}`),
};
