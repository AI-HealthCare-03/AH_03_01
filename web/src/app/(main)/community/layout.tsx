"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import PopularPostsWidget from "@/components/community/PopularPostsWidget";
import TodayQuizWidget from "@/components/community/TodayQuizWidget";

const SIDEBAR_NAV = [
  { href: "/community/notice", label: "📌 공지사항" },
  { href: "/community/board", label: "📰 정보공유" },
  { href: "/community/free", label: "💬 자유게시판" },
  { href: "/community/quiz", label: "🧠 건강 퀴즈" },
] as const;

const CATEGORIES = [
  { label: "고혈압", value: "HYPERTENSION" },
  { label: "당뇨", value: "DIABETES" },
  { label: "심혈관", value: "CARDIOVASCULAR" },
  { label: "생활습관", value: "LIFESTYLE" },
] as const;

function SidebarCategories() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeCategory = searchParams.get("info_category");
  const isBoard = pathname.startsWith("/community/board");

  return (
    <>
      {CATEGORIES.map(({ label, value }) => (
        <Link
          key={value}
          href={`/community/board?info_category=${value}`}
          className={[
            "px-3 py-1.5 rounded-[8px] text-sm transition-colors",
            isBoard && activeCategory === value
              ? "bg-brand text-brand-black font-medium"
              : "text-text-secondary hover:bg-surface hover:text-text-primary",
          ].join(" ")}
        >
          {label}
        </Link>
      ))}
    </>
  );
}

export default function CommunityLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-6 md:px-10 md:py-8">
      <div className="flex gap-8">
        {/* 좌측 사이드바 */}
        <aside className="hidden md:flex flex-col gap-1 w-44 shrink-0">
          {SIDEBAR_NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={[
                "px-3 py-2 rounded-[8px] text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "bg-brand text-brand-black"
                  : "text-text-secondary hover:bg-surface hover:text-text-primary",
              ].join(" ")}
            >
              {label}
            </Link>
          ))}

          <p className="mt-4 px-3 text-xs font-semibold text-text-disabled uppercase tracking-wide">
            카테고리
          </p>
          <Suspense fallback={null}>
            <SidebarCategories />
          </Suspense>
        </aside>

        {/* 콘텐츠 영역 */}
        <div className="flex-1 min-w-0">{children}</div>

        {/* 우측 사이드바 */}
        <aside className="hidden lg:flex flex-col gap-4 w-60 shrink-0">
          <PopularPostsWidget />
          {!pathname.startsWith("/community/quiz") && <TodayQuizWidget />}
        </aside>
      </div>
    </div>
  );
}
