"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Activity, Trophy, MessageCircle, User } from "lucide-react";
import ProfileDropdown from "@/components/layout/ProfileDropdown";
import { usePointBalance } from "@/hooks/queries/usePointBalance";

/* =========================================
   GNB (Global Navigation Bar)
   데스크탑: 상단 수평 헤더
   모바일: 하단 5탭 탭바
   ========================================= */

const NAV_ITEMS = [
  { href: "/", label: "홈", icon: Home },
  { href: "/health-records", label: "건강", icon: Activity },
  { href: "/challenges", label: "챌린지", icon: Trophy },
  { href: "/community", label: "커뮤니티", icon: MessageCircle },
  { href: "/mypage", label: "마이", icon: User },
] as const;

export default function GNB() {
  const pathname = usePathname();

  return (
    <>
      {/* 데스크탑 상단 헤더 */}
      <header className="hidden md:flex items-center justify-between px-8 h-16 border-b border-border bg-white sticky top-0 z-40">
        {/* 로고 */}
        <Link href="/" className="text-xl font-black text-brand-black">
          헬씨루틴
        </Link>

        {/* 네비 링크 */}
        <nav aria-label="메인 메뉴">
          <ul className="flex items-center gap-1">
            {NAV_ITEMS.map(({ href, label }) => {
              const isActive =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={[
                      "px-4 py-2 rounded-[8px] text-sm font-medium transition-colors",
                      isActive
                        ? "bg-brand text-brand-black"
                        : "text-text-secondary hover:text-text-primary hover:bg-surface",
                    ].join(" ")}
                    aria-current={isActive ? "page" : undefined}
                  >
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* 우측: 포인트 + 프로필 드롭다운 */}
        <HeaderRight />
      </header>

      {/* 모바일 하단 탭바 */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-border safe-bottom"
        aria-label="하단 탭 메뉴"
      >
        <ul className="flex items-center">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const isActive =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href} className="flex-1">
                <Link
                  href={href}
                  className={[
                    "flex flex-col items-center justify-center gap-1 py-2 min-h-[56px]",
                    "text-[10px] font-medium transition-colors",
                    isActive ? "text-brand-black" : "text-text-tertiary",
                  ].join(" ")}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon
                    size={22}
                    strokeWidth={isActive ? 2.5 : 1.8}
                    aria-hidden="true"
                  />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}

function HeaderRight() {
  const { data: balance } = usePointBalance(0);
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-semibold text-text-primary">
        {(balance?.balance ?? 0).toLocaleString()} P
      </span>
      <ProfileDropdown />
    </div>
  );
}
