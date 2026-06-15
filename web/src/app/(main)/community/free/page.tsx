"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listPosts } from "@/lib/api/community";
import PostCard from "@/components/community/PostCard";

export default function FreeBoardPage() {
  const { data: pinnedData } = useQuery({
    queryKey: ["posts", "NOTICE", "pinned"],
    queryFn: () => listPosts({ category: "NOTICE", size: 10 }),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["posts", "FREE"],
    queryFn: () => listPosts({ category: "FREE", size: 50 }),
    refetchOnMount: true,
  });

  const pinnedNotices = pinnedData?.items.filter((p) => p.is_pinned) ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-black text-text-primary">자유게시판</h1>
        <Link
          href="/community/free/new"
          className="px-3 py-1.5 text-sm font-semibold bg-brand-black text-white rounded-[8px] hover:opacity-80 transition-opacity"
        >
          글쓰기
        </Link>
      </div>

      {/* 공지 고정 게시글 */}
      {pinnedNotices.length > 0 && (
        <div className="flex flex-col gap-2 mb-4">
          {pinnedNotices.map((post) => (
            <PostCard key={post.id} post={post} basePath="/community/notice" />
          ))}
        </div>
      )}

      {isLoading ? (
        <p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>
      ) : !data?.items.length ? (
        <p className="py-12 text-center text-sm text-text-tertiary">아직 게시글이 없어요.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {data.items.map((post) => <PostCard key={post.id} post={post} basePath="/community/free" />)}
        </div>
      )}
    </div>
  );
}
