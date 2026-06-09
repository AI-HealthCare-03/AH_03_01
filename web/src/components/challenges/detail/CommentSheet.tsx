"use client";

import { useState, useEffect, useRef } from "react";
import { useVerificationComments } from "@/hooks/queries/useVerificationComments";
import { useCreateReaction } from "@/hooks/queries/useCreateReaction";
import { COMMENTS_KEY } from "@/hooks/queries/useVerificationComments";
import { createReply } from "@/lib/api/challenge";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import ReportModal from "@/components/community/ReportModal";
import { format, parseISO } from "@/lib/dateUtils";
import type { VerificationFeedItem, ReactionWithReplies } from "@/types/challenge";

interface CommentSheetProps {
  post: VerificationFeedItem | null;
  onClose: () => void;
}

function CommentItem({
  comment,
  verificationId,
  onReplySuccess,
}: {
  comment: ReactionWithReplies;
  verificationId: number;
  onReplySuccess: () => void;
}) {
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { showToast } = useToast();

  const handleReport = (id: number) => setReportId(id);

  const handleReply = async () => {
    if (!replyText.trim()) return;
    setSubmitting(true);
    try {
      await createReply(verificationId, comment.id, replyText.trim());
      setReplyText("");
      setShowReplyInput(false);
      onReplySuccess();
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="py-3">
      {/* 댓글 */}
      <div className="flex gap-2">
        <div className="w-8 h-8 rounded-full bg-brand flex items-center justify-center text-xs font-bold shrink-0">
          {(comment.user?.nickname ?? comment.user?.name ?? "U")[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 mb-0.5">
            <span className="text-sm font-semibold text-text-primary">
              {comment.user?.nickname ?? comment.user?.name ?? "유저"}
            </span>
            <span className="text-xs text-text-tertiary">
              {format(parseISO(comment.created_at), "M월 d일 HH:mm")}
            </span>
          </div>
          <p className="text-sm text-text-primary leading-relaxed break-words">
            {comment.content}
          </p>
          <div className="flex gap-3 mt-1">
            <button
              type="button"
              onClick={() => setShowReplyInput((v) => !v)}
              className="text-xs text-text-tertiary hover:text-text-secondary"
            >
              답글
            </button>
            <button
              type="button"
              onClick={() => handleReport(comment.id)}
              className="text-xs text-text-tertiary hover:text-status-danger"
            >
              신고
            </button>
          </div>
        </div>
      </div>

      {/* 대댓글 목록 */}
      {comment.replies.length > 0 && (
        <div className="ml-10 mt-2 space-y-2 border-l-2 border-border pl-3">
          {comment.replies.map((reply) => (
            <div key={reply.id} className="flex gap-2">
              <div className="w-6 h-6 rounded-full bg-surface flex items-center justify-center text-xs font-bold shrink-0">
                {(reply.user?.nickname ?? reply.user?.name ?? "U")[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-0.5">
                  <span className="text-xs font-semibold text-text-primary">
                    {reply.user?.nickname ?? reply.user?.name ?? "유저"}
                  </span>
                  <span className="text-xs text-text-tertiary">
                    {format(parseISO(reply.created_at), "M월 d일 HH:mm")}
                  </span>
                </div>
                <p className="text-xs text-text-primary leading-relaxed break-words">
                  {reply.content}
                </p>
                <button
                  type="button"
                  onClick={() => handleReport(reply.id)}
                  className="text-xs text-text-tertiary hover:text-status-danger mt-0.5"
                >
                  신고
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 답글 입력 */}
      {showReplyInput && (
        <div className="ml-10 mt-2 flex gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleReply(); } }}
            placeholder="답글을 입력하세요..."
            maxLength={500}
            className="flex-1 px-3 py-2 text-sm border border-border rounded-[10px] focus:outline-none focus:border-brand-black"
            autoFocus
          />
          <button
            type="button"
            onClick={handleReply}
            disabled={!replyText.trim() || submitting}
            className="px-3 py-2 text-sm font-semibold bg-brand rounded-[10px] disabled:opacity-40"
          >
            등록
          </button>
        </div>
      )}
    </div>
  );
}

export default function CommentSheet({ post, onClose }: CommentSheetProps) {
  const qc = useQueryClient();
  const { data: reactionsData, isLoading } = useVerificationComments(post?.id ?? null);
  const commentMutation = useCreateReaction(post?.id ?? 0);
  const [commentText, setCommentText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();
  const [reportId, setReportId] = useState<number | null>(null);

  useEffect(() => {
    if (post) {
      setCommentText("");
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [post?.id]);

  if (!post) return null;

  const handleAddComment = () => {
    if (!commentText.trim()) return;
    commentMutation.mutate(
      { type: "COMMENT", content: commentText.trim() },
      {
        onSuccess: () => {
          setCommentText("");
          qc.invalidateQueries({ queryKey: [COMMENTS_KEY, post.id] });
        },
        onError: (err) => showToast(extractErrorMessage(err), "error"),
      }
    );
  };

  const methodLabel =
    post.method === "CHECK"
      ? "✅ 체크 인증"
      : post.method === "PHOTO"
      ? "📸 사진 인증"
      : "🛡️ 방지권";

  return (
    <>
      {reportId !== null && (
        <ReportModal targetType="COMMENT" targetId={reportId} onClose={() => setReportId(null)} />
      )}

      {/* 딤 배경 */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 시트 */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-[20px] max-h-[80vh] flex flex-col shadow-xl">
        {/* 핸들 */}
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="w-10 h-1 bg-border rounded-full" />
        </div>

        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
          <span className="text-sm font-bold text-text-primary">댓글 {reactionsData?.comments.length ?? 0}개</span>
          <button type="button" onClick={onClose} className="text-text-tertiary hover:text-text-primary text-xl leading-none">
            ✕
          </button>
        </div>

        {/* 원글 미리보기 */}
        <div className="px-5 py-3 bg-surface border-b border-border shrink-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-text-primary">
              {post.user_nickname ?? "유저"}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white border border-border text-text-secondary">
              {methodLabel}
            </span>
          </div>
          {post.caption && (
            <p className="text-sm text-text-secondary leading-relaxed line-clamp-2">
              {post.caption}
            </p>
          )}
        </div>

        {/* 댓글 목록 */}
        <div className="flex-1 overflow-y-auto px-5 divide-y divide-border">
          {isLoading ? (
            <div className="py-8 text-center">
              <p className="text-sm text-text-tertiary">불러오는 중...</p>
            </div>
          ) : reactionsData?.comments.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-text-tertiary">첫 댓글을 남겨보세요!</p>
            </div>
          ) : (
            reactionsData?.comments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                verificationId={post.id}
                onReplySuccess={() =>
                  qc.invalidateQueries({ queryKey: [COMMENTS_KEY, post.id] })
                }
              />
            ))
          )}
        </div>

        {/* 댓글 입력 */}
        <div className="px-4 py-3 border-t border-border bg-white shrink-0 flex gap-2 pb-safe">
          <input
            ref={inputRef}
            type="text"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAddComment(); } }}
            placeholder="댓글을 입력하세요..."
            maxLength={500}
            className="flex-1 px-4 py-2.5 text-sm border border-border rounded-full focus:outline-none focus:border-brand-black bg-surface"
          />
          <button
            type="button"
            onClick={handleAddComment}
            disabled={!commentText.trim() || commentMutation.isPending}
            className="w-10 h-10 rounded-full bg-brand flex items-center justify-center disabled:opacity-40 shrink-0"
            aria-label="댓글 등록"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 8L14 2L10 8L14 14L2 8Z" fill="currentColor" />
            </svg>
          </button>
        </div>
      </div>
    </>
  );
}
