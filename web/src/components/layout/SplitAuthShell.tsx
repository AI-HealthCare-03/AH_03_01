import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";

/* =========================================
   SplitAuthShell
   데스크탑: 좌 브랜드 패널(크림) 50% + 우 흰색 폼 50%
   모바일: 단일 컬럼
   ========================================= */

interface SplitAuthShellProps {
  children: ReactNode;
}

const FEATURES = [
  {
    bg: "bg-red-100",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
        <path d="M12 2C12 2 5 10 5 15a7 7 0 0014 0C19 10 12 2 12 2z" fill="#EF4444"/>
      </svg>
    ),
    label: "혈당 기록",
  },
  {
    bg: "bg-red-100",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
        <path d="M12 21l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.18L12 21z" fill="#EF4444"/>
      </svg>
    ),
    label: "혈압 관리",
  },
  {
    bg: "bg-green-100",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
        <path d="M17 8C8 10 5.9 16.17 3.82 21c2.18-1.44 4.34-1.57 5.87-1.1C12 18.27 16 15 17 8z" fill="#22C55E"/>
        <path d="M17 8c0 8-5 13-12 13" stroke="#22C55E" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    label: "식단 관리",
  },
  {
    bg: "bg-blue-100",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
        <circle cx="13" cy="4" r="2" fill="#3B82F6"/>
        <path d="M7 22l3-6 2 2 3-5 2 4" stroke="#3B82F6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M7 13l2-5 3 2 2-4" stroke="#3B82F6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    label: "운동 기록",
  },
  {
    bg: "bg-amber-100",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
        <rect x="5" y="3" width="14" height="18" rx="2" stroke="#F59E0B" strokeWidth="1.8"/>
        <path d="M9 8h6M9 12h6M9 16h4" stroke="#F59E0B" strokeWidth="1.8" strokeLinecap="round"/>
        <path d="M9 3v2M15 3v2" stroke="#F59E0B" strokeWidth="1.8" strokeLinecap="round"/>
      </svg>
    ),
    label: "기록 요약",
  },
];

export default function SplitAuthShell({ children }: SplitAuthShellProps) {
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* 좌: 브랜드 패널 (데스크탑만) — 50% */}
      <div className="split-auth-left hidden md:flex md:w-1/2 flex-shrink-0 bg-[#FFFBEB] flex-col px-10 pt-8 pb-6 sticky top-0 h-screen overflow-hidden">

        {/* 로고 */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-5">
          <span className="w-10 h-10 shrink-0 rounded-xl bg-[#FFFBEB] flex items-center justify-center">
            <Image src="/images/logo.png" alt="케어로그 로고" width={36} height={36} className="object-contain" unoptimized/>
          </span>
          <div className="flex flex-col">
            <span className="text-xl font-black text-text-primary tracking-tight leading-none">케어로그</span>
            <span className="text-[11px] text-text-tertiary leading-none font-medium mt-0.5">CareLog</span>
          </div>
        </Link>

        {/* 헤드라인 */}
        <h1 className="text-4xl xl:text-5xl font-black text-text-primary leading-[1.15] mb-3">
          매일의 <span className="text-amber-500">케어</span>,<br />
          건강의 <span className="text-amber-500">기록</span>
        </h1>
        <p className="text-sm text-text-secondary leading-relaxed mb-5">
          혈당·혈압·식단·운동을 쉽고 간편하게 기록하고,<br />
          건강한 습관으로 더 나은 내일을 만들어 보세요.
        </p>

        {/* 기능 목록 + 마스코트 (나란히) */}
        <div className="flex-1 flex gap-4 items-center min-h-0">
          {/* 기능 목록 */}
          <ul className="space-y-3 shrink-0">
            {FEATURES.map(({ bg, icon, label }) => (
              <li key={label} className="flex items-center gap-3">
                <span className={`w-8 h-8 rounded-full ${bg} flex items-center justify-center shrink-0`}>
                  {icon}
                </span>
                <span className="text-sm font-semibold text-text-primary">{label}</span>
              </li>
            ))}
          </ul>

          {/* 마스코트 */}
          <div className="flex-1 flex items-center justify-center min-h-0">
            <Image
              src="/images/mascot.png"
              alt="케어로그 마스코트"
              width={280}
              height={280}
              className="object-contain drop-shadow-xl w-auto max-h-[280px]"
              priority
              unoptimized
            />
          </div>
        </div>

        {/* 하단 tagline 카드 */}
        <div className="split-auth-tagline mt-4 bg-amber-100 border border-amber-200 rounded-2xl px-4 py-3 flex items-center gap-3 shrink-0">
          <Image src="/images/checklogo.png" alt="케어로그 아이콘" width={40} height={40} className="shrink-0 object-contain" unoptimized/>
          <p className="text-xs text-amber-900/80 leading-relaxed font-medium">
            케어로그는 당신의 매일을 기록하고, 더 건강한 내일로 이어주는 든든한 동반자입니다.
          </p>
        </div>
      </div>

      {/* 우: 폼 영역 — 50%, 흰색 배경 */}
      <div className="flex-1 flex flex-col min-h-screen md:min-h-0 bg-white">
        {/* 모바일 헤더 */}
        <div className="md:hidden flex items-center gap-2 px-5 py-4 border-b border-border">
          <span className="w-8 h-8 shrink-0 rounded-lg bg-white flex items-center justify-center">
            <Image src="/images/logo.png" alt="케어로그 로고" width={28} height={28} className="object-contain" unoptimized/>
          </span>
          <span className="text-lg font-black text-text-primary">케어로그</span>
        </div>

        {/* 폼 컨텐츠 — 각 페이지에서 카드 직접 구성 */}
        <div className="flex-1 overflow-y-auto">
          {children}
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
