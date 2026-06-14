"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { listPosts } from "@/lib/api/community";
import InfoPostCard from "@/components/community/InfoPostCard";
import PostCard from "@/components/community/PostCard";
import type { InfoCategory } from "@/types/community";

const VALID_INFO_CATEGORIES: InfoCategory[] = ["HYPERTENSION", "DIABETES", "CARDIOVASCULAR", "LIFESTYLE"];

const CATEGORY_LABEL: Record<InfoCategory, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
  LIFESTYLE: "생활습관",
};

function BoardContent() {
  const searchParams = useSearchParams();
  const raw = searchParams.get("info_category");
  const infoCategory: InfoCategory | null =
    raw && (VALID_INFO_CATEGORIES as string[]).includes(raw) ? (raw as InfoCategory) : null;

  const { data: pinnedData } = useQuery({
    queryKey: ["posts", "NOTICE", "pinned"],
    queryFn: () => listPosts({ category: "NOTICE", size: 10 }),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["posts", "INFO", infoCategory],
    queryFn: () => listPosts({ category: "INFO", size: 50, info_category: infoCategory }),
    refetchOnMount: true,
  });

  const pinnedNotices = pinnedData?.items.filter((p) => p.is_pinned) ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-black text-text-primary">정보공유</h1>
          {infoCategory && (
            <span className="text-sm text-text-secondary">· {CATEGORY_LABEL[infoCategory]}</span>
          )}
        </div>
        <Link
          href="/community/board/new?category=INFO"
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

      {/* 정보공유 카드 그리드 */}
      {isLoading ? (
        <p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>
      ) : !data?.items.length ? (
        <p className="py-12 text-center text-sm text-text-tertiary">아직 게시글이 없어요.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {data.items.map((post) => (
            <InfoPostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function BoardPage() {
  return (
    <Suspense fallback={<p className="py-12 text-center text-sm text-text-tertiary">불러오는 중...</p>}>
      <BoardContent />
    </Suspense>
  );
}
