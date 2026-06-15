"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMe } from "@/hooks/queries/useMe";

const NAV = [
  { href: "/admin", label: "대시보드", icon: "📊", exact: true },
  { href: "/admin/users", label: "회원 관리", icon: "👥" },
  { href: "/admin/challenges", label: "챌린지 관리", icon: "🏃" },
  { href: "/admin/community", label: "커뮤니티 관리", icon: "📝" },
  { href: "/admin/support", label: "고객 문의", icon: "📨" },
  { href: "/admin/notices", label: "공지사항", icon: "📢" },
  { href: "/admin/faq", label: "FAQ 관리", icon: "❓" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: me, isLoading } = useMe();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (!me) { router.replace("/login"); return; }
    if (!me.is_admin) { router.replace("/"); }
  }, [me, isLoading, router]);

  if (isLoading || !me?.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#111]">
        <p className="text-white text-sm animate-pulse">확인 중…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#111]">
      {/* 사이드바 오버레이 (모바일) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 사이드바 */}
      <aside
        className={[
          "fixed top-0 left-0 h-full w-60 bg-[#1a1a1a] border-r border-white/10 z-30 flex flex-col transition-transform duration-200",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        ].join(" ")}
      >
        {/* 로고 */}
        <div className="px-5 py-5 border-b border-white/10">
          <p className="text-brand font-black text-lg leading-none">AH Admin</p>
          <p className="text-white/40 text-xs mt-1">관리자 콘솔</p>
        </div>

        {/* 내비게이션 */}
        <nav className="flex-1 overflow-y-auto py-4 space-y-0.5 px-2">
          {NAV.map(({ href, label, icon, exact }) => {
            const active = exact ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={[
                  "flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-sm font-medium transition-colors",
                  active
                    ? "bg-brand text-brand-black"
                    : "text-white/60 hover:bg-white/5 hover:text-white",
                ].join(" ")}
              >
                <span aria-hidden="true">{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* 하단 */}
        <div className="px-5 py-4 border-t border-white/10">
          <p className="text-xs text-white/40 truncate">{me.email}</p>
          <Link href="/" className="text-xs text-white/40 hover:text-white transition-colors mt-1 block">
            ← 서비스로 돌아가기
          </Link>
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <div className="flex-1 lg:ml-60 flex flex-col min-h-screen">
        {/* 상단 바 */}
        <header className="sticky top-0 z-10 bg-[#1a1a1a] border-b border-white/10 px-5 py-3 flex items-center gap-3">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-white/60 hover:text-white text-xl"
            aria-label="메뉴 열기"
          >
            ☰
          </button>
          <p className="text-white/60 text-sm">
            {NAV.find((n) => (n.exact ? pathname === n.href : pathname.startsWith(n.href)))?.label ?? "관리자"}
          </p>
        </header>

        <main className="flex-1 p-6 text-white">
          {children}
        </main>
      </div>
    </div>
  );
}
