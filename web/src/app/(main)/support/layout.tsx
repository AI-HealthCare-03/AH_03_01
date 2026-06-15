"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const NAV = [
  { href: "/support", label: "🏠 고객센터 홈" },
  { href: "/support/inquiry", label: "💬 1:1 문의" },
  { href: "/support/terms/service", label: "📄 약관" },
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/support") return pathname === "/support";
  if (href === "/support/terms/service") return pathname.startsWith("/support/terms");
  return pathname.startsWith(href);
}

export default function SupportLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-6 md:px-10 md:py-8">
      <div className="flex gap-8">
        {/* 좌측 사이드바 — desktop only */}
        <aside className="hidden md:flex flex-col gap-1 w-44 shrink-0">
          <p className="px-3 mb-2 text-xs font-semibold text-text-disabled uppercase tracking-wide">
            고객지원
          </p>
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={[
                "px-3 py-2 rounded-[8px] text-sm font-medium transition-colors",
                isActive(pathname, href)
                  ? "bg-brand text-brand-black"
                  : "text-text-secondary hover:bg-surface hover:text-text-primary",
              ].join(" ")}
            >
              {label}
            </Link>
          ))}
        </aside>

        {/* 콘텐츠 영역 */}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  );
}
