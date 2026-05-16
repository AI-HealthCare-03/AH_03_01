import type { ReactNode } from "react";
import Link from "next/link";

/* =========================================
   SplitAuthShell
   데스크탑: 좌 브랜드 패널(노랑) + 우 폼
   모바일: 단일 컬럼
   ========================================= */

interface SplitAuthShellProps {
  children: ReactNode;
  /** 브랜드 패널 하단 보조 텍스트 */
  brandSubtext?: string;
}

export default function SplitAuthShell({
  children,
  brandSubtext,
}: SplitAuthShellProps) {
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* 좌: 브랜드 패널 (데스크탑만) */}
      <div className="hidden md:flex md:w-[420px] lg:w-[480px] xl:w-[520px] flex-shrink-0 bg-brand flex-col justify-between p-10 sticky top-0 h-screen">
        <div>
          {/* 로고 */}
          <Link href="/" className="inline-flex items-center gap-2 mb-16">
            <span className="text-2xl font-black text-brand-black tracking-tight">
              헬씨루틴
            </span>
          </Link>

          {/* 메인 카피 */}
          <h1 className="text-4xl lg:text-5xl font-black text-brand-black leading-tight">
            매일 5분으로
            <br />
            만성질환을
            <br />
            관리해요
          </h1>

          {brandSubtext && (
            <p className="mt-6 text-sm text-brand-black/70 leading-relaxed">
              {brandSubtext}
            </p>
          )}
        </div>

        {/* 하단: 캐릭터 이모지 + 면책 안내 */}
        <div>
          <div className="text-5xl mb-4">🐣</div>
          <p className="text-xs text-brand-black/60 leading-relaxed">
            본 서비스는 의학적 진단을 대체하지 않습니다.
            <br />
            건강 관련 이상이 있으면 반드시 전문의와 상담하세요.
          </p>
        </div>
      </div>

      {/* 우: 폼 영역 */}
      <div className="flex-1 flex flex-col min-h-screen md:min-h-0">
        {/* 모바일 헤더 */}
        <div className="md:hidden flex items-center justify-between px-5 py-4 border-b border-border">
          <Link href="/" className="text-xl font-black text-brand-black">
            헬씨루틴
          </Link>
        </div>

        {/* 폼 컨텐츠 */}
        <div className="flex-1 flex items-start md:items-center justify-center px-5 md:px-10 py-8 md:py-12 overflow-y-auto">
          <div className="w-full max-w-[480px]">{children}</div>
        </div>

        {/* 모바일 면책 */}
        <div className="md:hidden px-5 py-4 border-t border-border">
          <p className="text-xs text-text-tertiary text-center">
            본 서비스는 의학적 진단을 대체하지 않습니다.
          </p>
        </div>
      </div>
    </div>
  );
}
