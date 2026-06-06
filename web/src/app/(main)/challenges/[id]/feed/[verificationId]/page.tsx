"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChallengeFeed } from "@/hooks/queries/useChallengeFeed";
import { useVerificationComments, COMMENTS_KEY } from "@/hooks/queries/useVerificationComments";
import { useToggleLike } from "@/hooks/queries/useToggleLike";
import { useCreateReaction } from "@/hooks/queries/useCreateReaction";
import { createReply, deleteReaction } from "@/lib/api/challenge";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { format, parseISO } from "@/lib/dateUtils";
import { useMe } from "@/hooks/queries/useMe";
import type { VerificationFeedItem, ReactionWithReplies, VerificationReaction } from "@/types/challenge";

/* =========================================
   인증 게시물 상세 + 댓글 페이지
   /challenges/[id]/feed/[verificationId]
   ========================================= */

interface PageProps {
  params: Promise<{ id: string; verificationId: string }>;
}

/* ── 사진 미리보기 ── */
function PhotoPreview({ fileId }: { fileId: number }) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    import("@/lib/api/client").then(({ default: apiClient }) => {
      apiClient
        .get(`/api/v1/files/${fileId}`)
        .then(({ data }: { data: { access_url: string } }) => {
            const resolved = data.access_url.startsWith("http")
              ? data.access_url
              : `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}${data.access_url}`;
            setUrl(resolved);
          })
        .catch(() => {})
        .finally(() => setLoading(false));
    });
  }, [fileId]);

  if (loading) return <div className="w-full aspect-video bg-surface animate-pulse rounded-[12px]" />;
  if (!url) return (
    <div className="w-full aspect-video bg-surface rounded-[12px] flex items-center justify-center">
      <span className="text-4xl" aria-hidden="true">📸</span>
    </div>
  );
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img src={url} alt="인증 사진" className="w-full aspect-video object-cover rounded-[12px]" />
  );
}

/* ── 댓글 단건 ── */
function CommentItem({
  comment,
  verificationId,
  myUserId,
  onSuccess,
}: {
  comment: ReactionWithReplies;
  verificationId: number;
  myUserId: string | undefined;
  onSuccess: () => void;
}) {
  const [showReply, setShowReply] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { showToast } = useToast();

  const handleDelete = async () => {
    if (!confirm("댓글을 삭제할까요?")) return;
    setDeleting(true);
    try {
      await deleteReaction(verificationId, comment.id);
      onSuccess();
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteReply = async (replyId: number) => {
    if (!confirm("답글을 삭제할까요?")) return;
    try {
      await deleteReaction(verificationId, replyId);
      onSuccess();
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  const handleReply = async () => {
    if (!replyText.trim()) return;
    setSubmitting(true);
    try {
      await createReply(verificationId, comment.id, replyText.trim());
      setReplyText("");
      setShowReply(false);
      onSuccess();
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setSubmitting(false);
    }
  };

  const nickname = (c: VerificationReaction) =>
    c.user?.nickname ?? c.user?.name ?? "유저";

  return (
    <div className="py-4 border-b border-border last:border-0">
      {/* 댓글 본문 */}
      <div className="flex gap-3">
        <div className="w-8 h-8 rounded-full bg-brand flex items-center justify-center text-xs font-bold shrink-0">
          {nickname(comment)[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-sm font-semibold text-text-primary">{nickname(comment)}</span>
            <span className="text-xs text-text-tertiary">
              {format(parseISO(comment.created_at), "M월 d일 HH:mm")}
            </span>
          </div>
          <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap break-words">
            {comment.content}
          </p>
          <div className="flex gap-4 mt-2">
            <button
              type="button"
              onClick={() => setShowReply((v) => !v)}
              className="text-xs text-text-tertiary hover:text-text-secondary font-medium"
            >
              답글 달기
            </button>
            {myUserId === String(comment.user_id) ? (
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="text-xs text-text-tertiary hover:text-status-danger disabled:opacity-40"
              >
                삭제
              </button>
            ) : (
              <button
                type="button"
                onClick={() => showToast("신고가 접수되었어요.", "info")}
                className="text-xs text-text-tertiary hover:text-status-danger"
              >
                신고
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 대댓글 목록 */}
      {comment.replies.length > 0 && (
        <div className="ml-11 mt-3 space-y-3">
          {comment.replies.map((reply) => (
            <div key={reply.id} className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-surface border border-border flex items-center justify-center text-xs font-bold shrink-0">
                {nickname(reply)[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-0.5">
                  <span className="text-xs font-semibold text-text-primary">{nickname(reply)}</span>
                  <span className="text-xs text-text-tertiary">
                    {format(parseISO(reply.created_at), "M월 d일 HH:mm")}
                  </span>
                </div>
                <p className="text-xs text-text-primary leading-relaxed whitespace-pre-wrap break-words">
                  {reply.content}
                </p>
                {myUserId === String(reply.user_id) ? (
                  <button
                    type="button"
                    onClick={() => handleDeleteReply(reply.id)}
                    className="text-xs text-text-tertiary hover:text-status-danger mt-1"
                  >
                    삭제
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => showToast("신고가 접수되었어요.", "info")}
                    className="text-xs text-text-tertiary hover:text-status-danger mt-1"
                  >
                    신고
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 답글 입력 */}
      {showReply && (
        <div className="ml-11 mt-3">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="답글을 입력하세요..."
            rows={2}
            maxLength={500}
            className="w-full px-3 py-2 text-sm border border-border rounded-[10px] resize-none focus:outline-none focus:border-brand-black"
          />
          <div className="flex justify-end gap-2 mt-1">
            <button
              type="button"
              onClick={() => { setShowReply(false); setReplyText(""); }}
              className="text-xs text-text-tertiary hover:text-text-secondary px-3 py-1.5"
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleReply}
              disabled={!replyText.trim() || submitting}
              className="text-xs font-semibold bg-brand px-4 py-1.5 rounded-[8px] disabled:opacity-40"
            >
              등록
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FeedDetailPage({ params }: PageProps) {
  const { id, verificationId } = use(params);
  const challengeId = parseInt(id, 10);
  const verificationIdNum = parseInt(verificationId, 10);
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const { data: feedData } = useChallengeFeed(challengeId);
  const { data: reactionsData, isLoading: commentsLoading } = useVerificationComments(verificationIdNum);
  const { data: me } = useMe();
  const toggleLikeMutation = useToggleLike(challengeId);
  const commentMutation = useCreateReaction(verificationIdNum);

  const post: VerificationFeedItem | undefined = feedData?.items.find(
    (item) => item.id === verificationIdNum
  );

  const [liked, setLiked] = useState(post?.my_like ?? false);
  const [likeCount, setLikeCount] = useState(post?.like_count ?? 0);
  const [commentText, setCommentText] = useState("");

  useEffect(() => {
    if (post) {
      setLiked(post.my_like);
      setLikeCount(post.like_count);
    }
  }, [post?.id]);

  const handleLike = () => {
    const next = !liked;
    setLiked(next);
    setLikeCount((c) => c + (next ? 1 : -1));
    toggleLikeMutation.mutate(verificationIdNum, {
      onError: (err) => {
        setLiked(!next);
        setLikeCount((c) => c + (next ? -1 : 1));
        showToast(extractErrorMessage(err), "error");
      },
    });
  };

  const handleComment = () => {
    if (!commentText.trim()) return;
    commentMutation.mutate(
      { type: "COMMENT", content: commentText.trim() },
      {
        onSuccess: () => {
          setCommentText("");
          qc.invalidateQueries({ queryKey: [COMMENTS_KEY, verificationIdNum] });
        },
        onError: (err) => showToast(extractErrorMessage(err), "error"),
      }
    );
  };

  const isTimer = post?.method === "CHECK" && !!post?.verified_duration_seconds;

  const methodLabel =
    isTimer ? "⏱️ 타이머 인증"
    : post?.method === "CHECK" ? "✅ 체크 인증"
    : post?.method === "PHOTO" ? "📸 사진 인증"
    : "🛡️ 방지권";

  const methodColor =
    isTimer ? "bg-surface text-text-secondary"
    : post?.method === "CHECK" ? "bg-status-success-bg text-status-success"
    : post?.method === "PHOTO" ? "bg-status-info-bg text-status-info"
    : "bg-surface text-text-secondary";

  return (
    <div className="max-w-2xl mx-auto px-5 py-6">
      {/* 뒤로가기 */}
      <button
        type="button"
        onClick={() => router.push(`/challenges/${challengeId}?tab=chat`)}
        className="text-sm text-text-tertiary hover:text-text-secondary mb-5 inline-flex items-center gap-1"
      >
        ← 소통 탭으로
      </button>

      {/* 게시물 */}
      {post ? (
        <div className="bg-white border border-border rounded-[16px] p-5 mb-6">
          {/* 헤더 */}
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-brand flex items-center justify-center text-sm font-bold shrink-0">
              {(post.user_nickname ?? "U")[0].toUpperCase()}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-text-primary">
                  {post.user_nickname ?? "유저"}
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${methodColor}`}>
                  {methodLabel}
                </span>
              </div>
              <p className="text-xs text-text-tertiary mt-0.5">
                {format(parseISO(post.created_at), "M월 d일 HH:mm")}
              </p>
            </div>
          </div>

          {/* 사진 */}
          {post.photo_file_id && (
            <div className="mb-4">
              <PhotoPreview fileId={post.photo_file_id} />
            </div>
          )}

          {/* caption */}
          {post.caption && (
            <p className="text-sm text-text-primary leading-relaxed mb-4 whitespace-pre-wrap">
              {post.caption}
            </p>
          )}

          {/* 좋아요 */}
          <div className="flex items-center gap-1 pt-3 border-t border-border">
            <button
              type="button"
              onClick={handleLike}
              disabled={toggleLikeMutation.isPending}
              className={[
                "flex items-center gap-1.5 text-sm transition-colors",
                liked ? "text-status-danger" : "text-text-tertiary hover:text-status-danger",
              ].join(" ")}
            >
              <span className="text-base">{liked ? "❤️" : "🤍"}</span>
              {likeCount > 0 && <span className="text-xs font-medium">{likeCount}</span>}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-border rounded-[16px] p-5 mb-6 animate-pulse h-32" />
      )}

      {/* 댓글 목록 */}
      <div className="mb-6">
        <h2 className="text-sm font-bold text-text-primary mb-2">
          댓글 {reactionsData?.comments.length ?? 0}개
        </h2>
        {commentsLoading ? (
          <div className="space-y-4">
            {[0, 1].map((i) => (
              <div key={i} className="h-16 bg-surface rounded-[12px] animate-pulse" />
            ))}
          </div>
        ) : reactionsData?.comments.length === 0 ? (
          <p className="text-sm text-text-tertiary py-6 text-center">첫 댓글을 남겨보세요!</p>
        ) : (
          <div className="bg-white border border-border rounded-[16px] px-5 divide-y divide-border">
            {reactionsData?.comments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                verificationId={verificationIdNum}
                myUserId={me?.id}
                onSuccess={() =>
                  qc.invalidateQueries({ queryKey: [COMMENTS_KEY, verificationIdNum] })
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* 댓글 작성 */}
      <div className="bg-white border border-border rounded-[16px] p-5">
        <p className="text-sm font-bold text-text-primary mb-3">댓글 작성</p>
        <textarea
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          placeholder="댓글을 입력하세요..."
          rows={4}
          maxLength={500}
          className="w-full px-4 py-3 text-sm border border-border rounded-[12px] resize-none focus:outline-none focus:border-brand-black"
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-text-tertiary">{commentText.length}/500</span>
          <button
            type="button"
            onClick={handleComment}
            disabled={!commentText.trim() || commentMutation.isPending}
            className="px-5 py-2 text-sm font-bold bg-brand rounded-[10px] disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            {commentMutation.isPending ? "등록 중..." : "댓글 등록"}
          </button>
        </div>
      </div>
    </div>
  );
}
