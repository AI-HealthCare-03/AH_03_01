import apiClient from "./client";
import type {
  PostListResponse,
  PostDetail,
  PostCreateRequest,
  PostUpdateRequest,
  PostCategory,
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
