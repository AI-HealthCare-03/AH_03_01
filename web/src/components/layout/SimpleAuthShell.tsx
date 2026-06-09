import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

/* =========================================
   SimpleAuthShell
   단순 auth 페이지 (SMS, 비번찾기 등)
   모바일: 뒤로가기 헤더 + 단일 컬럼
   데스크탑: 좌 패딩 없는 2단 (선택) 또는 중앙 컨테이너
   ========================================= */

interface SimpleAuthShellProps {
  children: ReactNode;
  title?: string;
  backHref?: string;
  /** true = 데스크탑에서도 중앙 정렬 컨테이너만 */
  centerOnly?: boolean;
}

export default function SimpleAuthShell({
  children,
  title,
  backHref,
  centerOnly = false,
}: SimpleAuthShellProps) {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* 헤더 */}
      <header className="flex items-center gap-3 px-5 py-4 border-b border-border">
        {backHref ? (
          <Link
            href={backHref}
            className="flex items-center justify-center w-9 h-9 -ml-2 rounded-full hover:bg-surface transition-colors"
            aria-label="뒤로가기"
          >
            <ChevronLeft size={22} className="text-text-primary" />
          </Link>
        ) : (
          <Link href="/" className="text-xl font-black text-brand-black">
            케어로그
          </Link>
        )}
        {title && (
          <h1 className="text-base font-semibold text-text-primary">{title}</h1>
        )}
      </header>

      {/* 컨텐츠 */}
      <main
        className={[
          "flex-1 flex px-5 py-8",
          centerOnly
            ? "justify-center items-start"
            : "justify-center items-start",
        ].join(" ")}
      >
        <div className="w-full max-w-[480px]">{children}</div>
      </main>

      {/* 면책 */}
      <footer className="px-5 py-4 border-t border-border">
        <p className="text-xs text-text-tertiary text-center">
          본 서비스는 의학적 진단을 대체하지 않습니다.
        </p>
      </footer>
    </div>
  );
}
