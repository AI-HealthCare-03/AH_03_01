export type PostCategory = "NOTICE" | "INFO" | "FREE";

export interface PostListItem {
  id: number;
  title: string;
  category: PostCategory;
  is_pinned: boolean;
  view_count: number;
  author_id: string;
  author_nickname: string | null;
  created_at: string;
}

export interface PostDetail extends PostListItem {
  content: string;
  updated_at: string;
}

export interface PostListResponse {
  items: PostListItem[];
  total: number;
  page: number;
  size: number;
}

export interface PostCreateRequest {
  title: string;
  content: string;
  category: PostCategory;
}

export interface PostUpdateRequest {
  title?: string;
  content?: string;
  category?: PostCategory;
}

export interface Comment {
  id: number;
  content: string;
  author_id: string;
  author_nickname: string | null;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
  replies: Comment[];
}

export interface CommentCreateRequest {
  content: string;
  parent_id?: number;
}
