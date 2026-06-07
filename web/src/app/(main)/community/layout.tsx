"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/* =========================================
   커뮤니티 공통 레이아웃 — 사이드바 + 콘텐츠
   ========================================= */

const SIDEBAR_NAV = [
  { href: "/community/notice", label: "📌 공지사항" },
  { href: "/community/board", label: "📰 정보공유" },
  { href: "/community/free", label: "💬 자유게시판" },
  { href: "/community/quiz", label: "🧠 건강 퀴즈" },
] as const;

const CATEGORIES = ["고혈압", "당뇨", "심혈관", "생활습관"] as const;

export default function CommunityLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-6 md:px-10 md:py-8">
      <div className="flex gap-8">
        {/* 사이드바 (데스크탑만) */}
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
          {CATEGORIES.map((cat) => (
            <span
              key={cat}
              className="px-3 py-1.5 rounded-[8px] text-sm text-text-secondary cursor-default"
            >
              {cat}
            </span>
          ))}
        </aside>

        {/* 콘텐츠 영역 */}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  );
}
