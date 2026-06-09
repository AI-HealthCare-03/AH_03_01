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

export async function uploadImage(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post<{ url: string }>("/api/v1/posts/images", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return resolveMediaUrl(res.data.url) ?? res.data.url;
}
