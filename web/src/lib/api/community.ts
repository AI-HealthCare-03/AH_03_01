import apiClient from "./client";
import { resolveMediaUrl } from "@/lib/api/media";
import type {
  PostListResponse,
  PostDetail,
  PostCreateRequest,
  PostUpdateRequest,
  PostCategory,
  Comment,
  CommentCreateRequest,
  ReportCreateRequest,
  TodayQuizResponse,
  QuizResponse,
  QuizAnswerRequest,
  QuizAnswerResponse,
  QuizAttemptHistoryItem,
} from "@/types/community";

export async function listPosts(params?: {
  page?: number;
  size?: number;
  category?: PostCategory;
}): Promise<PostListResponse> {
  const res = await apiClient.get<PostListResponse>("/api/v1/posts", { params });
  return res.data;
}

export async function getPost(id: number): Promise<PostDetail> {
  const res = await apiClient.get<PostDetail>(`/api/v1/posts/${id}`);
  return res.data;
}

export async function createPost(data: PostCreateRequest): Promise<PostDetail> {
  const res = await apiClient.post<PostDetail>("/api/v1/posts", data);
  return res.data;
}

export async function updatePost(id: number, data: PostUpdateRequest): Promise<PostDetail> {
  const res = await apiClient.patch<PostDetail>(`/api/v1/posts/${id}`, data);
  return res.data;
}

export async function deletePost(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/posts/${id}`);
}

export async function listComments(postId: number): Promise<Comment[]> {
  const res = await apiClient.get<Comment[]>(`/api/v1/posts/${postId}/comments`);
  return res.data;
}

export async function createComment(postId: number, data: CommentCreateRequest): Promise<Comment> {
  const res = await apiClient.post<Comment>(`/api/v1/posts/${postId}/comments`, data);
  return res.data;
}

export async function updateComment(postId: number, commentId: number, data: { content: string }): Promise<Comment> {
  const res = await apiClient.patch<Comment>(`/api/v1/posts/${postId}/comments/${commentId}`, data);
  return res.data;
}

export async function deleteComment(postId: number, commentId: number): Promise<void> {
  await apiClient.delete(`/api/v1/posts/${postId}/comments/${commentId}`);
}

export async function createReport(data: ReportCreateRequest): Promise<{ message: string }> {
  const res = await apiClient.post<{ message: string }>("/api/v1/reports", data);
  return res.data;
}

// ── Quiz ──────────────────────────────────────────────────────────────────────
export async function getAvailableQuizzes(): Promise<QuizResponse[]> {
  const res = await apiClient.get<QuizResponse[]>("/api/v1/quizzes/available");
  return res.data;
}

export async function getTodayQuiz(): Promise<TodayQuizResponse> {
  const res = await apiClient.get<TodayQuizResponse>("/api/v1/quizzes/today");
  return res.data;
}

export async function answerQuiz(quizId: number, data: QuizAnswerRequest): Promise<QuizAnswerResponse> {
  const res = await apiClient.post<QuizAnswerResponse>(`/api/v1/quizzes/${quizId}/answer`, data);
  return res.data;
}

export async function getQuizHistory(params?: { page?: number; size?: number }): Promise<QuizAttemptHistoryItem[]> {
  const res = await apiClient.get<QuizAttemptHistoryItem[]>("/api/v1/quizzes/history", { params });
  return res.data;
}

export async function uploadImage(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post<{ url: string }>("/api/v1/posts/images", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return resolveMediaUrl(res.data.url) ?? res.data.url;
}
