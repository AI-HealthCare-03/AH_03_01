"use client";

/* =========================================
   인사 배너 컴포넌트
   - 닉네임/name fallback 하이라이트
   - 데스크탑: 일러스트 자리 + 2버튼
   - 모바일: 등급 배지 칩
   ========================================= */

import Link from "next/link";
import Button from "@/components/ui/Button";
import type { Me } from "@/types/api";

interface WelcomeBannerProps {
  user: Me | undefined;
  activeChallengeCount: number;
  pendingChallengeCount: number;
  isLoading: boolean;
}

export default function WelcomeBanner({
  user,
  activeChallengeCount,
  pendingChallengeCount,
  isLoading,
}: WelcomeBannerProps) {
  const displayName = user?.nickname ?? user?.name ?? "사용자";

  return (
    <section
      aria-label="환영 배너"
      className="rounded-[20px] bg-brand-black text-white px-6 py-7 md:px-10 md:py-10 relative overflow-hidden"
    >
      <div className="flex items-start justify-between gap-4">
        {/* 좌측 텍스트 영역 */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-brand opacity-90 mb-2">
            🌱 오늘도 함께해요
          </p>

          {isLoading ? (
            <div className="space-y-2">
              <div className="h-7 w-48 bg-white/10 rounded animate-pulse" />
              <div className="h-5 w-64 bg-white/10 rounded animate-pulse" />
            </div>
          ) : (
            <>
              <h1 className="text-[22px] md:text-[26px] font-bold leading-tight mb-1">
                안녕하세요,{" "}
                <span className="text-brand">{displayName}</span> 님
              </h1>
              <p className="text-sm text-white/70 font-medium">
                건강한 하루 시작해요
              </p>

              <p className="mt-3 text-xs text-white/50 leading-relaxed">
                {activeChallengeCount > 0 ? (
                  <>
                    진행중인 챌린지{" "}
                    <span className="text-brand font-semibold">
                      {activeChallengeCount}개
                    </span>
                    {pendingChallengeCount > 0 && (
                      <>
                        , 오늘 인증해야 할 챌린지{" "}
                        <span className="text-brand font-semibold">
                          {pendingChallengeCount}개
                        </span>
                        가 있어요.
                      </>
                    )}
                  </>
                ) : (
                  "챌린지를 시작해 건강한 습관을 만들어 보세요."
                )}
              </p>
            </>
          )}

          {/* 데스크탑 CTA 버튼 */}
          <div className="hidden md:flex items-center gap-3 mt-6">
            <Button
              variant="primary"
              size="sm"
              className="!bg-brand !text-brand-black font-semibold"
            >
              <Link href="/challenges">오늘 챌린지 인증하기</Link>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="!text-white/70 hover:!text-white border border-white/20 hover:!bg-white/10"
            >
              <Link href="/predictions">위험도 자세히 보기</Link>
            </Button>
          </div>
        </div>

        {/* 우측: 데스크탑 일러스트 / 모바일 등급 배지 */}
        <div className="flex-shrink-0">
          {/* 데스크탑 일러스트 placeholder */}
          <div
            className="hidden md:flex w-32 h-32 rounded-[16px] bg-white/10 items-center justify-center text-5xl"
            aria-hidden="true"
          >
            🏃
          </div>

          {/* 모바일 등급 배지 */}
          <Link
            href="/predictions"
            className="md:hidden flex items-center gap-1 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-xs font-medium text-white/80 hover:bg-white/20 transition-colors whitespace-nowrap"
            aria-label="위험도 자세히 보기"
          >
            위험도 확인
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>
    </section>
  );
}
