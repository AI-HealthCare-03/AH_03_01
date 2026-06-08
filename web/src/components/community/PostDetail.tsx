"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPost, deletePost } from "@/lib/api/community";
import { renderMarkdown } from "@/components/community/MarkdownEditor";
import { useMe } from "@/hooks/queries/useMe";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { PostCategory } from "@/types/community";

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

  const { mutate: remove, isPending } = useMutation({
    mutationFn: () => deletePost(postId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      router.push(post ? BACK_PATH[post.category] : "/community/board");
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  if (isLoading) return <p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>;
  if (!post) return <p className="py-12 text-center text-sm text-text-tertiary">게시글을 찾을 수 없어요.</p>;

  const isAuthor = me?.id === post.author_id;
  const backPath = BACK_PATH[post.category];

  return (
    <div className="bg-white border border-border rounded-[16px] p-6">
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <p className="text-xs text-text-tertiary mb-1">
            {post.author_nickname ?? "익명"} · 조회 {post.view_count} ·{" "}
            {new Date(post.created_at).toLocaleDateString("ko-KR")}
          </p>
          <h1 className="text-lg font-bold text-text-primary">{post.title}</h1>
        </div>
        {isAuthor && (
          <div className="flex gap-2 shrink-0">
            <Link
              href={`/community/board/${postId}/edit`}
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
          </div>
        )}
      </div>

      <hr className="border-border mb-4" />

      {/* 본문 */}
      <div
        className="text-sm text-text-primary leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(post.content) }}
      />

      <hr className="border-border mt-6 mb-4" />

      <Link href={backPath} className="text-sm text-text-secondary hover:text-text-primary transition-colors">
        ← 목록으로
      </Link>
    </div>
  );
}
