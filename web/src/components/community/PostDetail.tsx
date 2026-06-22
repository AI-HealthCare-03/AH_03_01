"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPost, deletePost, likePost, unlikePost } from "@/lib/api/community";
import type { PostDetail as PostDetailType } from "@/types/community";
import CommentSection from "@/components/community/CommentSection";
import ReportModal from "@/components/community/ReportModal";
import { renderMarkdown } from "@/components/community/MarkdownEditor";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { useState } from "react";
import type { PostCategory, InfoCategory } from "@/types/community";

const INFO_CATEGORY_LABEL: Record<InfoCategory, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
  LIFESTYLE: "생활습관",
};

const INFO_CATEGORY_COLOR: Record<InfoCategory, string> = {
  HYPERTENSION: "bg-red-100 text-red-700",
  DIABETES: "bg-blue-100 text-blue-700",
  CARDIOVASCULAR: "bg-purple-100 text-purple-700",
  LIFESTYLE: "bg-green-100 text-green-700",
};

const BACK_PATH: Record<PostCategory, string> = {
  INFO: "/community/board",
  FREE: "/community/free",
  NOTICE: "/community/notice",
};

export default function PostDetail({ postId }: { postId: number }) {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data: me } = useMe();

  const { data: post, isLoading } = useQuery({
    queryKey: ["post", postId],
    queryFn: () => getPost(postId),
  });

  const [showReport, setShowReport] = useState(false);

  const { mutate: remove, isPending } = useMutation({
    mutationFn: () => deletePost(postId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      router.push(post ? BACK_PATH[post.category] : "/community/board");
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const updateLikeCache = (data: { like_count: number; is_liked: boolean }) => {
    qc.setQueryData<PostDetailType>(["post", postId], (old) =>
      old ? { ...old, like_count: data.like_count, is_liked: data.is_liked } : old
    );
    qc.invalidateQueries({ queryKey: ["posts"] });
  };

  const { mutate: like, isPending: liking } = useMutation({
    mutationFn: () => likePost(postId),
    onSuccess: updateLikeCache,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const { mutate: unlike, isPending: unliking } = useMutation({
    mutationFn: () => unlikePost(postId),
    onSuccess: updateLikeCache,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  if (isLoading) return <p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>;
  if (!post) return <p className="py-12 text-center text-sm text-text-tertiary">게시글을 찾을 수 없어요.</p>;

  const isAuthor = me?.id === post.author_id;
  const backPath = BACK_PATH[post.category];

  return (
    <div className="bg-white border border-border rounded-[16px] p-6">
      {showReport && <ReportModal targetType="POST" targetId={postId} onClose={() => setShowReport(false)} />}
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            {post.category === "INFO" && post.info_category && (
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${INFO_CATEGORY_COLOR[post.info_category]}`}>
                {INFO_CATEGORY_LABEL[post.info_category]}
              </span>
            )}
            <p className="text-xs text-text-tertiary">
              {post.author_nickname ?? "익명"} · 조회 {post.view_count} ·{" "}
              {new Date(post.created_at).toLocaleDateString("ko-KR")}
            </p>
          </div>
          <h1 className="text-lg font-bold text-text-primary">{post.title}</h1>
        </div>
        <div className="flex gap-2 shrink-0">
          {isAuthor ? (
            <>
              <Link
                href={`${backPath}/${postId}/edit`}
                className="px-3 py-1.5 text-xs font-semibold border border-border rounded-[8px] hover:bg-surface transition-colors"
              >
                수정
              </Link>
              <button
                type="button"
                onClick={() => remove()}
                disabled={isPending}
                className="px-3 py-1.5 text-xs font-semibold bg-red-50 text-red-600 border border-red-200 rounded-[8px] hover:bg-red-100 transition-colors disabled:opacity-50"
              >
                삭제
              </button>
            </>
          ) : me && (
            <button
              type="button"
              onClick={() => setShowReport(true)}
              className="px-3 py-1.5 text-xs font-semibold border border-border rounded-[8px] hover:bg-surface transition-colors"
            >
              신고
            </button>
          )}
        </div>
      </div>

      <hr className="border-border mb-4" />

      {/* 본문 */}
      <div
        className="text-sm text-text-primary leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(post.content) }}
      />

      {/* 좋아요 · 댓글 수 */}
      <div className="flex items-center gap-4 mt-6 mb-4">
        <button
          type="button"
          disabled={!me || liking || unliking}
          onClick={() => (post.is_liked ? unlike() : like())}
          className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-red-500 disabled:cursor-default transition-colors"
        >
          <span className={post.is_liked ? "text-red-500" : ""}>{post.is_liked ? "❤️" : "🤍"}</span>
          <span className={post.is_liked ? "text-red-500" : ""}>{post.like_count}</span>
        </button>
        <span className="flex items-center gap-1.5 text-sm text-text-secondary">
          <span>💬</span>
          <span>{post.comment_count}</span>
          <span>댓글</span>
        </span>
      </div>

      <hr className="border-border mb-4" />

      <CommentSection postId={postId} />

      <hr className="border-border mt-6 mb-4" />

      <Link href={backPath} className="text-sm text-text-secondary hover:text-text-primary transition-colors">
        ← 목록으로
      </Link>
    </div>
  );
}
