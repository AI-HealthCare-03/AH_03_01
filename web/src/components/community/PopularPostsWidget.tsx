"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getPopularPosts } from "@/lib/api/community";
import type { PostCategory } from "@/types/community";

const BASE_PATH: Record<PostCategory, string> = {
  NOTICE: "/community/notice",
  INFO: "/community/board",
  FREE: "/community/free",
};

export default function PopularPostsWidget() {
  const { data } = useQuery({
    queryKey: ["posts", "popular"],
    queryFn: () => getPopularPosts(3),
    staleTime: 1000 * 60 * 5,
  });

  return (
    <div className="rounded-[16px] border border-border bg-white p-4 flex flex-col gap-3">
      <p className="text-sm font-bold text-text-primary">🔥 인기 글 (이번주)</p>
      {!data?.length ? (
        <p className="text-xs text-text-tertiary py-1">아직 인기 글이 없어요.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {data.map((post) => (
            <Link
              key={post.id}
              href={`${BASE_PATH[post.category]}/${post.id}`}
              className="flex flex-col gap-0.5 hover:opacity-70 transition-opacity"
            >
              <p className="text-xs font-medium text-text-primary line-clamp-2 leading-snug">{post.title}</p>
              <p className="text-[11px] text-text-tertiary">조회 {post.view_count}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
