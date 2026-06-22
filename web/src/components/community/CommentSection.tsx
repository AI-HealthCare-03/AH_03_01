"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listComments, createComment, updateComment, deleteComment, likeComment, unlikeComment } from "@/lib/api/community";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import ReportModal from "@/components/community/ReportModal";
import type { Comment } from "@/types/community";

// ── 답글 아이템 ─────────────────────────────────────────────────────────────────
interface ReplyItemProps {
  reply: Comment;
  myId: string | undefined;
  postId: number;
  parentId: number;
}

function ReplyItem({ reply, myId, postId, parentId }: ReplyItemProps) {
  const qc = useQueryClient();
  const { showToast } = useToast();

  const updateReplyLike = (data: { like_count: number; is_liked: boolean }) => {
    qc.setQueryData<Comment[]>(["comments", postId], (old) =>
      old?.map((c) =>
        c.id === parentId
          ? { ...c, replies: c.replies.map((r) => (r.id === reply.id ? { ...r, ...data } : r)) }
          : c
      ) ?? []
    );
  };

  const { mutate: like, isPending: liking } = useMutation({
    mutationFn: () => likeComment(postId, reply.id),
    onSuccess: updateReplyLike,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const { mutate: unlike, isPending: unliking } = useMutation({
    mutationFn: () => unlikeComment(postId, reply.id),
    onSuccess: updateReplyLike,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  return (
    <div>
      <p className="text-xs text-text-tertiary mb-0.5">
        {reply.author_nickname ?? "익명"} · {new Date(reply.created_at).toLocaleDateString("ko-KR")}
      </p>
      <p className="text-sm text-text-primary whitespace-pre-wrap">{reply.content}</p>
      <button
        type="button"
        disabled={!myId || liking || unliking}
        onClick={() => (reply.is_liked ? unlike() : like())}
        className="flex items-center gap-1 mt-1 text-xs text-text-secondary hover:text-red-500 disabled:cursor-default transition-colors"
      >
        <span className={reply.is_liked ? "text-red-500" : ""}>{reply.is_liked ? "❤️" : "🤍"}</span>
        <span className={reply.is_liked ? "text-red-500" : ""}>{reply.like_count}</span>
      </button>
    </div>
  );
}

// ── 댓글 아이템 ─────────────────────────────────────────────────────────────────
interface CommentItemProps {
  comment: Comment;
  myId: string | undefined;
  postId: number;
  onMutated: () => void;
  onReport: (id: number) => void;
}

function CommentItem({ comment, myId, postId, onMutated, onReport }: CommentItemProps) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const isAuthor = myId === comment.author_id;
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(comment.content);
  const [replyOpen, setReplyOpen] = useState(false);
  const [replyText, setReplyText] = useState("");

  const { mutate: save, isPending: saving } = useMutation({
    mutationFn: () => updateComment(postId, comment.id, { content: editText }),
    onSuccess: () => { setEditing(false); onMutated(); },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const { mutate: remove, isPending: removing } = useMutation({
    mutationFn: () => deleteComment(postId, comment.id),
    onSuccess: onMutated,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const { mutate: reply, isPending: replying } = useMutation({
    mutationFn: () => createComment(postId, { content: replyText, parent_id: comment.id }),
    onSuccess: () => { setReplyOpen(false); setReplyText(""); onMutated(); },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const updateCommentLike = (data: { like_count: number; is_liked: boolean }) => {
    qc.setQueryData<Comment[]>(["comments", postId], (old) =>
      old?.map((c) => (c.id === comment.id ? { ...c, ...data } : c)) ?? []
    );
  };

  const { mutate: like, isPending: liking } = useMutation({
    mutationFn: () => likeComment(postId, comment.id),
    onSuccess: updateCommentLike,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const { mutate: unlike, isPending: unliking } = useMutation({
    mutationFn: () => unlikeComment(postId, comment.id),
    onSuccess: updateCommentLike,
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  return (
    <div className="py-3 border-b border-border last:border-none">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-text-tertiary">
          {comment.author_nickname ?? "익명"} · {new Date(comment.created_at).toLocaleDateString("ko-KR")}
        </p>
        <div className="flex gap-3">
          {isAuthor ? (
            <>
              <button type="button" onClick={() => setEditing(true)} className="text-xs text-text-secondary hover:text-text-primary">수정</button>
              <button type="button" onClick={() => remove()} disabled={removing} className="text-xs text-red-500 hover:text-red-700 disabled:opacity-40">삭제</button>
            </>
          ) : myId ? (
            <button type="button" onClick={() => onReport(comment.id)} className="text-xs text-text-tertiary hover:text-text-secondary">신고</button>
          ) : null}
          {comment.parent_id === null && myId && (
            <button type="button" onClick={() => setReplyOpen((v) => !v)} className="text-xs text-text-secondary hover:text-text-primary">
              {replyOpen ? "취소" : "답글"}
            </button>
          )}
        </div>
      </div>

      {/* 본문 */}
      {editing ? (
        <div className="flex gap-2 mt-1">
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={2}
            className="flex-1 resize-none border border-border rounded-[10px] px-3 py-2 text-sm focus:outline-none focus:border-brand"
          />
          <div className="flex flex-col gap-1 self-end">
            <button type="button" onClick={() => editText.trim() && save()} disabled={saving || !editText.trim()} className="px-3 py-1.5 bg-brand-black text-white text-xs rounded-[8px] disabled:opacity-40">저장</button>
            <button type="button" onClick={() => { setEditing(false); setEditText(comment.content); }} className="px-3 py-1.5 border border-border text-xs rounded-[8px]">취소</button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-text-primary whitespace-pre-wrap">{comment.content}</p>
      )}

      {/* 댓글 좋아요 — 본문 바로 아래 */}
      <button
        type="button"
        disabled={!myId || liking || unliking}
        onClick={() => (comment.is_liked ? unlike() : like())}
        className="flex items-center gap-1 mt-1.5 text-xs text-text-secondary hover:text-red-500 disabled:cursor-default transition-colors"
      >
        <span className={comment.is_liked ? "text-red-500" : ""}>{comment.is_liked ? "❤️" : "🤍"}</span>
        <span className={comment.is_liked ? "text-red-500" : ""}>{comment.like_count}</span>
      </button>

      {/* 답글 목록 */}
      {comment.replies.length > 0 && (
        <div className="mt-2 pl-4 border-l-2 border-border space-y-2">
          {comment.replies.map((r) => (
            <ReplyItem key={r.id} reply={r} myId={myId} postId={postId} parentId={comment.id} />
          ))}
        </div>
      )}

      {/* 답글 입력 */}
      {replyOpen && (
        <div className="mt-2 pl-4 flex gap-2">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="답글을 입력하세요"
            rows={2}
            className="flex-1 resize-none border border-border rounded-[10px] px-3 py-2 text-sm focus:outline-none focus:border-brand"
          />
          <button
            type="button"
            onClick={() => replyText.trim() && reply()}
            disabled={replying || !replyText.trim()}
            className="px-3 py-2 bg-brand-black text-white text-xs rounded-[8px] disabled:opacity-40 self-end"
          >
            등록
          </button>
        </div>
      )}
    </div>
  );
}

// ── 댓글 섹션 ───────────────────────────────────────────────────────────────────
export default function CommentSection({ postId }: { postId: number }) {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const { showToast } = useToast();
  const [text, setText] = useState("");
  const [reportId, setReportId] = useState<number | null>(null);

  const { data: comments = [] } = useQuery({
    queryKey: ["comments", postId],
    queryFn: () => listComments(postId),
  });

  const onMutated = () => qc.invalidateQueries({ queryKey: ["comments", postId] });

  const { mutate: submit, isPending } = useMutation({
    mutationFn: () => createComment(postId, { content: text }),
    onSuccess: () => { onMutated(); setText(""); },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  return (
    <div className="mt-6">
      <h2 className="text-sm font-bold text-text-primary mb-3">댓글 {comments.length}개</h2>

      <div>
        {comments.length === 0 ? (
          <p className="py-4 text-sm text-text-tertiary text-center">첫 댓글을 남겨보세요.</p>
        ) : (
          comments.map((c) => (
            <CommentItem key={c.id} comment={c} myId={me?.id} postId={postId} onMutated={onMutated} onReport={setReportId} />
          ))
        )}
      </div>

      {reportId !== null && (
        <ReportModal targetType="COMMENT" targetId={reportId} onClose={() => setReportId(null)} />
      )}

      {me && (
        <div className="mt-4 flex gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="댓글을 입력하세요"
            rows={2}
            className="flex-1 resize-none border border-border rounded-[10px] px-3 py-2 text-sm focus:outline-none focus:border-brand"
          />
          <button
            type="button"
            onClick={() => text.trim() && submit()}
            disabled={isPending || !text.trim()}
            className="px-4 py-2 bg-brand-black text-white text-sm font-semibold rounded-[10px] disabled:opacity-40 self-end"
          >
            등록
          </button>
        </div>
      )}
    </div>
  );
}
