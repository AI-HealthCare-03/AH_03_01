"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listComments, createComment, updateComment, deleteComment } from "@/lib/api/community";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { Comment } from "@/types/community";

interface CommentItemProps {
  comment: Comment;
  myId: string | undefined;
  postId: number;
  onMutated: () => void;
}

function CommentItem({ comment, myId, postId, onMutated }: CommentItemProps) {
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

  return (
    <div className="py-3 border-b border-border last:border-none">
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
            <button type="button" onClick={() => showToast("신고가 접수되었습니다.", "success")} className="text-xs text-text-tertiary hover:text-text-secondary">신고</button>
          ) : null}
          {comment.parent_id === null && myId && (
            <button type="button" onClick={() => setReplyOpen((v) => !v)} className="text-xs text-text-secondary hover:text-text-primary">
              {replyOpen ? "취소" : "답글"}
            </button>
          )}
        </div>
      </div>

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

      {comment.replies.length > 0 && (
        <div className="mt-2 pl-4 border-l-2 border-border space-y-2">
          {comment.replies.map((r) => (
            <div key={r.id}>
              <p className="text-xs text-text-tertiary mb-0.5">
                {r.author_nickname ?? "익명"} · {new Date(r.created_at).toLocaleDateString("ko-KR")}
              </p>
              <p className="text-sm text-text-primary whitespace-pre-wrap">{r.content}</p>
            </div>
          ))}
        </div>
      )}

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

export default function CommentSection({ postId }: { postId: number }) {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const { showToast } = useToast();
  const [text, setText] = useState("");

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
            <CommentItem key={c.id} comment={c} myId={me?.id} postId={postId} onMutated={onMutated} />
          ))
        )}
      </div>

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
