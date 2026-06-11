export type PostCategory = "NOTICE" | "INFO" | "FREE";

export interface PostListItem {
  id: number;
  title: string;
  category: PostCategory;
  is_pinned: boolean;
  view_count: number;
  comment_count: number;
  like_count: number;
  author_id: string;
  author_nickname: string | null;
  created_at: string;
}

export interface PostDetail extends PostListItem {
  content: string;
  updated_at: string;
  is_liked: boolean;
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
  like_count: number;
  is_liked: boolean;
  replies: Comment[];
}

export interface LikeResponse {
  like_count: number;
  is_liked: boolean;
}

export interface CommentCreateRequest {
  content: string;
  parent_id?: number;
}

export type ReportTargetType = "POST" | "COMMENT" | "VERIFICATION";
export type ReportReason = "ABUSE" | "MISINFORMATION" | "PRIVACY" | "AD" | "FRAUD" | "ETC";

export interface ReportCreateRequest {
  target_type: ReportTargetType;
  target_id: number;
  reason: ReportReason;
}

// ── Quiz ──────────────────────────────────────────────────────────────────────
export type QuizCategory = "BLOOD_SUGAR" | "BLOOD_PRESSURE" | "DIET" | "EXERCISE" | "GENERAL";
export type QuizOption = "A" | "B" | "C" | "D";

export interface QuizResponse {
  id: number;
  question: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  category: QuizCategory;
  quiz_date: string;
}

export interface TodayQuizResponse {
  quiz: QuizResponse;
  already_answered: boolean;
}

export interface QuizAnswerRequest {
  selected_option: QuizOption;
}

export interface QuizAnswerResponse {
  is_correct: boolean;
  correct_option: QuizOption;
  explanation: string;
  points_earned: number;
}

export interface QuizAttemptHistoryItem {
  quiz_id: number;
  quiz_date: string;
  question: string;
  category: QuizCategory;
  selected_option: QuizOption;
  is_correct: boolean;
  points_earned: number;
  attempted_at: string;
}
