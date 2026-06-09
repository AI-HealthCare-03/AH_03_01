"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listComments, createComment } from "@/lib/api/community";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { Comment } from "@/types/community";

function CommentItem({ comment }: { comment: Comment }) {
  return (
    <div className="py-3 border-b border-border last:border-none">
      <p className="text-xs text-text-tertiary mb-1">
        {comment.author_nickname ?? "익명"} · {new Date(comment.created_at).toLocaleDateString("ko-KR")}
      </p>
      <p className="text-sm text-text-primary whitespace-pre-wrap">{comment.content}</p>
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

  const { mutate: submit, isPending } = useMutation({
    mutationFn: () => createComment(postId, { content: text }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["comments", postId] });
      setText("");
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  return (
    <div className="mt-6">
      <h2 className="text-sm font-bold text-text-primary mb-3">댓글 {comments.length}개</h2>

      <div>
        {comments.length === 0 ? (
          <p className="py-4 text-sm text-text-tertiary text-center">첫 댓글을 남겨보세요.</p>
        ) : (
          comments.map((c) => <CommentItem key={c.id} comment={c} />)
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
