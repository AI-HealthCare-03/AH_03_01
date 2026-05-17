"use client";

/* =========================================
   내 현황 카드 (A 카드)
   - 펫 정보, 레벨, XP 진행률
   - 진행 중 챌린지 최대 3개
   ========================================= */

import Link from "next/link";
import type { MyPet, ChallengeItem, ChallengeCategory } from "@/types/api";
import { dDayLabel } from "@/lib/dateUtils";

/* 카테고리별 이모지 */
const CATEGORY_EMOJI: Record<ChallengeCategory, string> = {
  EXERCISE: "🚶",
  WATER: "💧",
  SLEEP: "🌅",
  DIET: "🥗",
  NO_SMOKING: "🚭",
  NO_ALCOHOL: "🚱",
  DISEASE_CARE: "💊",
  MEDITATION: "🧘",
  WEIGHT_MANAGEMENT: "⚖️",
};

interface MyStatusCardProps {
  pet: MyPet | null | undefined;
  challenges: ChallengeItem[];
  isLoading: boolean;
}

export default function MyStatusCard({
  pet,
  challenges,
  isLoading,
}: MyStatusCardProps) {
  const displayChallenges = challenges.slice(0, 3);
  const totalXp = pet ? pet.current_xp + pet.xp_to_next_level : 0;
  const xpPercent = pet
    ? Math.min(100, Math.round((pet.current_xp / totalXp) * 100))
    : 0;

  return (
    <article
      aria-label="내 현황"
      className="bg-white rounded-[16px] border border-border p-5 flex flex-col gap-4 shadow-sm"
    >
      {/* 헤더 */}
      <div className="flex items-center gap-2">
        <span className="text-xl" aria-hidden="true">👤</span>
        <h2 className="text-base font-bold text-text-primary">내 현황</h2>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <div className="h-4 w-32 bg-surface rounded animate-pulse" />
          <div className="h-3 w-full bg-surface rounded animate-pulse" />
          <div className="h-3 w-3/4 bg-surface rounded animate-pulse" />
        </div>
      ) : pet ? (
        <>
          {/* 펫 + 레벨 */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-text-primary truncate">
              {pet.name}
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-brand text-brand-black text-xs font-bold shrink-0">
              Lv.{pet.level}
            </span>
          </div>

          {/* XP 진행률 */}
          <div>
            <div className="flex justify-between text-xs text-text-tertiary mb-1">
              <span>
                {pet.name} · {pet.current_xp.toLocaleString()}/
                {totalXp.toLocaleString()} EXP
              </span>
              <span>{xpPercent}%</span>
            </div>
            <div
              className="h-2 bg-surface rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={xpPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="경험치 진행률"
            >
              <div
                className="h-full bg-brand rounded-full transition-all duration-500"
                style={{ width: `${xpPercent}%` }}
              />
            </div>
          </div>

          {/* 진행 중 챌린지 */}
          <div>
            <p className="text-xs font-semibold text-text-tertiary mb-2">
              진행 중인 챌린지
            </p>
            {displayChallenges.length > 0 ? (
              <ul className="space-y-2">
                {displayChallenges.map((ch) => (
                  <li
                    key={ch.id}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="flex items-center gap-1.5 text-xs text-text-secondary truncate">
                      <span aria-hidden="true">
                        {CATEGORY_EMOJI[ch.category]}
                      </span>
                      <span className="truncate">{ch.title}</span>
                    </span>
                    <span className="text-xs font-medium text-text-tertiary shrink-0">
                      {dDayLabel(ch.end_date)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-text-tertiary">
                진행 중인 챌린지가 없어요
              </p>
            )}
          </div>
        </>
      ) : (
        /* 펫 없는 신규 유저 */
        <div className="flex flex-col items-center py-4 gap-3 text-center">
          <span className="text-4xl" aria-hidden="true">🐣</span>
          <p className="text-sm text-text-secondary">
            아직 펫이 없어요
          </p>
          <Link
            href="/pets/create"
            className="text-xs font-semibold text-brand-black underline underline-offset-2"
          >
            펫 만들기 →
          </Link>
        </div>
      )}

      {/* 하단 링크 */}
      <div className="mt-auto pt-2 border-t border-border">
        <Link
          href="/challenges"
          className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
        >
          내 챌린지 보기 →
        </Link>
      </div>
    </article>
  );
}
