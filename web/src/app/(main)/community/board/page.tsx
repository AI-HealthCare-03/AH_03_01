"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listPosts } from "@/lib/api/community";
import type { PostListItem } from "@/types/community";

function PostCard({ post }: { post: PostListItem }) {
  return (
    <Link
      href={`/community/board/${post.id}`}
      className="block p-4 bg-white border border-border rounded-[12px] hover:shadow-sm transition-shadow"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            {post.is_pinned && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-red-100 text-red-600 rounded">
                📌 고정
              </span>
            )}
            <p className="text-sm font-semibold text-text-primary truncate">{post.title}</p>
          </div>
          <p className="text-xs text-text-tertiary">
            {post.author_nickname ?? "익명"} · 조회 {post.view_count} ·{" "}
            {new Date(post.created_at).toLocaleDateString("ko-KR")}
          </p>
        </div>
      </div>
    </Link>
  );
}

export default function BoardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["posts", "INFO"],
    queryFn: () => listPosts({ category: "INFO", size: 50 }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-text-primary">정보공유</h2>
        <Link
          href="/community/board/new"
          className="px-3 py-1.5 text-sm font-semibold bg-brand-black text-white rounded-[8px] hover:opacity-80 transition-opacity"
        >
          글쓰기
        </Link>
      </div>

      {isLoading ? (
        <p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>
      ) : !data?.items.length ? (
        <p className="py-12 text-center text-sm text-text-tertiary">아직 게시글이 없어요.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {data.items.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}
