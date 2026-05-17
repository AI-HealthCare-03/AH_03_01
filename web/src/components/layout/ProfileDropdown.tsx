"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useMe } from "@/hooks/queries/useMe";
import { useWeeklyXp } from "@/hooks/queries/useWeeklyXp";

/* =========================================
   헤더 우측 프로필 아바타 + 드롭다운
   - 마이페이지 링크
   - 이번 주 누적 EXP + 활동별 breakdown
   - 로그아웃
   ========================================= */

const XP_KIND_LABEL: Record<string, string> = {
  HEALTH_INPUT: "건강 데이터 입력",
  HEALTH_VIEW: "건강 데이터 확인",
  CHALLENGE_VERIFY: "챌린지 인증",
  POST: "게시글 작성",
  COMMENT: "댓글 작성",
  QUIZ: "퀴즈 풀이",
};

export default function ProfileDropdown() {
  const { logout } = useAuth();
  const { data: me } = useMe();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  /* 드롭다운이 열려 있을 때만 EXP 요청. 외부에서 사전로딩 X */
  const { data: xp, isLoading } = useWeeklyXp();

  /* 외부 클릭으로 닫기 */
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    if (open) {
      document.addEventListener("mousedown", onClick);
      document.addEventListener("keydown", onEsc);
    }
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  const initial = me?.name?.[0]?.toUpperCase() ?? "U";

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-8 h-8 rounded-full bg-brand flex items-center justify-center text-xs font-bold hover:ring-2 hover:ring-brand/40 focus:outline-none focus:ring-2 focus:ring-brand"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="내 메뉴 열기"
      >
        {initial}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-72 rounded-[14px] border border-border bg-white shadow-lg overflow-hidden z-50"
        >
          {/* 사용자 헤더 */}
          <div className="px-4 py-3 border-b border-border">
            <p className="text-sm font-bold text-text-primary truncate">
              {me?.name ?? "사용자"}
            </p>
            {me?.email ? (
              <p className="text-xs text-text-tertiary truncate">{me.email}</p>
            ) : null}
          </div>

          {/* 주간 EXP 카드 */}
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-xs font-semibold text-text-tertiary">
                이번 주 활동량
              </span>
              <span className="text-[11px] text-text-tertiary">
                {xp?.week_id ?? "—"}
              </span>
            </div>
            <p className="text-2xl font-black text-brand-black">
              {isLoading ? "…" : (xp?.total_points ?? 0).toLocaleString()}{" "}
              <span className="text-xs font-semibold text-text-secondary">
                EXP
              </span>
            </p>

            {xp?.items && xp.items.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {xp.items.map((it) => (
                  <li
                    key={it.kind}
                    className="flex items-center justify-between text-[11px] text-text-secondary"
                  >
                    <span>{XP_KIND_LABEL[it.kind] ?? it.kind}</span>
                    <span className="font-semibold text-text-primary">
                      +{it.points} EXP{" "}
                      <span className="text-text-tertiary">({it.count}회)</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[11px] text-text-tertiary mt-2">
                아직 이번 주 활동이 없어요
              </p>
            )}

            {/* 안내 */}
            <p className="mt-3 text-[10px] leading-snug text-text-tertiary">
              주간 1·2·3위에게 각각 500 / 300 / 100 P가 지급돼요. 매주 월요일에
              집계가 리셋됩니다.
            </p>
          </div>

          {/* 메뉴 항목 */}
          <nav className="py-1">
            <Link
              href="/mypage"
              role="menuitem"
              className="block px-4 py-2 text-sm text-text-primary hover:bg-surface"
              onClick={() => setOpen(false)}
            >
              마이페이지
            </Link>
            <Link
              href="/leaderboard"
              role="menuitem"
              className="block px-4 py-2 text-sm text-text-primary hover:bg-surface"
              onClick={() => setOpen(false)}
            >
              주간 리더보드 보기
            </Link>
            <button
              type="button"
              role="menuitem"
              className="block w-full text-left px-4 py-2 text-sm text-status-error hover:bg-surface"
              onClick={() => {
                setOpen(false);
                logout();
              }}
            >
              로그아웃
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}
