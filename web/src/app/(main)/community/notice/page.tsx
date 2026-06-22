"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listPosts } from "@/lib/api/community";
import PostCard from "@/components/community/PostCard";

export default function NoticePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["posts", "NOTICE"],
    queryFn: () => listPosts({ category: "NOTICE", size: 50 }),
    refetchOnMount: true,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-black text-text-primary">공지사항</h1>
        <Link
          href="/community/notice/new"
          className="px-3 py-1.5 text-sm font-semibold bg-brand-black text-white rounded-[8px] hover:opacity-80 transition-opacity"
        >
          글쓰기
        </Link>
      </div>
      {isLoading ? (
        <p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>
      ) : !data?.items.length ? (
        <p className="py-12 text-center text-sm text-text-tertiary">아직 공지사항이 없어요.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {data.items.map((post) => <PostCard key={post.id} post={post} basePath="/community/notice" />)}
        </div>
      )}
    </div>
  );
}
