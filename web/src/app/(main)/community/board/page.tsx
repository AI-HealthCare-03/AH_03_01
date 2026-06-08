"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listPosts } from "@/lib/api/community";
import PostCard from "@/components/community/PostCard";

export default function BoardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["posts", "INFO"],
    queryFn: () => listPosts({ category: "INFO", size: 50 }),
    refetchOnMount: true,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-text-primary">정보공유</h2>
        <Link
          href="/community/board/new?category=INFO"
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
          {data.items.map((post) => <PostCard key={post.id} post={post} />)}
        </div>
      )}
    </div>
  );
}
