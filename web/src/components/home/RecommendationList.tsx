"use client";

/* =========================================
   맞춤 추천 챌린지 섹션
   - 데스크탑: 3컬럼 그리드
   - 모바일: 가로 스크롤 스냅
   ========================================= */

import Link from "next/link";
import Button from "@/components/ui/Button";
import type {
  ChallengeRecommendationItem,
  RecommendationPriority,
} from "@/types/api";

interface RecommendationListProps {
  items: ChallengeRecommendationItem[];
  isLoading: boolean;
  hasPrediction: boolean;
  /** true 면 1컬럼 세로 리스트(우측 사이드 패널용). 기본은 3컬럼 그리드. */
  dense?: boolean;
  /** false 면 상단 헤더("맞춤 추천 챌린지" 타이틀) 숨김 — aside 에 자체 헤더 있을 때 */
  showHeader?: boolean;
}

/* 우선순위 → 배지 스타일. 백엔드 TOP/OPTIONAL 와 구 별칭 HIGHEST/SUPPLEMENTAL 모두 매핑 */
const TOP_STYLE = { label: "최우선", bg: "bg-[#ffeaea]", text: "text-[#e53935]" } as const;
const OPT_STYLE = { label: "보조", bg: "bg-surface", text: "text-text-tertiary" } as const;

const PRIORITY_CONFIG: Record<
  RecommendationPriority,
  { label: string; bg: string; text: string }
> = {
  TOP: TOP_STYLE,
  HIGHEST: TOP_STYLE,
  RECOMMENDED: {
    label: "권장",
    bg: "bg-brand-light",
    text: "text-[#856404]",
  },
  OPTIONAL: OPT_STYLE,
  SUPPLEMENTAL: OPT_STYLE,
};

function RecommendationCard({ item }: { item: ChallengeRecommendationItem }) {
  /* 미지의 priority 값에 대해 RECOMMENDED 로 fallback (crash 방지) */
  const priority = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.RECOMMENDED;
  /* 백엔드는 reward_points 를 보내지 않으므로 정책상 기본 200P 표시 */
  const rewardLabel = `${item.reward_points ?? 200}P`;

  return (
    <div className="snap-start shrink-0 w-[240px] md:w-auto bg-white rounded-[16px] border border-border p-4 flex flex-col gap-3 shadow-sm min-w-0">
      {/* 헤더 행 */}
      <div className="flex items-center justify-between gap-2">
        <span
          className={[
            "text-[10px] font-bold px-2 py-0.5 rounded-full",
            priority.bg,
            priority.text,
          ].join(" ")}
        >
          {priority.label}
        </span>
        <span className="text-xs font-bold text-brand-black">{rewardLabel}</span>
      </div>

      {/* 제목 */}
      <div>
        <p className="text-sm font-bold text-text-primary leading-snug mb-1">
          {item.title}
        </p>
        <p className="text-xs text-text-tertiary leading-relaxed line-clamp-2">
          {item.reason}
        </p>
      </div>

      {/* 시작 버튼 */}
      <div className="mt-auto">
        <Button
          variant="outline"
          size="sm"
          fullWidth
          className="text-xs"
          aria-label={`${item.title} 챌린지 시작하기`}
        >
          <Link href="/challenges">시작하기</Link>
        </Button>
      </div>
    </div>
  );
}

export default function RecommendationList({
  items,
  isLoading,
  hasPrediction,
  dense = false,
  showHeader = true,
}: RecommendationListProps) {
  return (
    <section aria-labelledby="recommendation-heading">
      {showHeader && (
        <div className="flex items-center justify-between mb-4">
          <h2
            id="recommendation-heading"
            className="text-base font-bold text-text-primary"
          >
            맞춤 추천 챌린지
          </h2>
          <Link
            href="/challenges"
            className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
          >
            전체 보기 →
          </Link>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-40 bg-white rounded-[16px] border border-border animate-pulse"
            />
          ))}
        </div>
      ) : !hasPrediction ? (
        <div className="bg-white rounded-[16px] border border-dashed border-border p-8 text-center shadow-sm">
          <p className="text-3xl mb-3" aria-hidden="true">🎯</p>
          <p className="text-sm font-semibold text-text-primary mb-1">
            맞춤 추천을 준비 중이에요
          </p>
          <p className="text-xs text-text-tertiary mb-4">
            건강 데이터와 위험도 예측이 완료되면 나에게 딱 맞는 챌린지를 추천해 드려요
          </p>
          <Link
            href="/health-records"
            className="text-sm font-semibold text-brand-black underline underline-offset-2"
          >
            건강 데이터 입력하기 →
          </Link>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-[16px] border border-dashed border-border p-8 text-center shadow-sm">
          <p className="text-sm text-text-tertiary">
            현재 추천 챌린지가 없어요
          </p>
        </div>
      ) : dense ? (
        /* 사이드 패널: 세로 1컬럼 */
        <div className="flex flex-col gap-3">
          {items.map((item, idx) => (
            <RecommendationCard
              key={item.template_id ?? item.challenge_id ?? item.id ?? idx}
              item={item}
            />
          ))}
        </div>
      ) : (
        /* 데스크탑: grid, 모바일: 가로 스크롤 */
        <>
          {/* 모바일용 가로 스크롤 */}
          <div className="flex md:hidden gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-5 px-5">
            {items.map((item, idx) => (
              <RecommendationCard
                key={item.template_id ?? item.challenge_id ?? item.id ?? idx}
                item={item}
              />
            ))}
          </div>
          {/* 데스크탑용 그리드 */}
          <div className="hidden md:grid grid-cols-3 gap-4">
            {items.map((item, idx) => (
              <RecommendationCard
                key={item.template_id ?? item.challenge_id ?? item.id ?? idx}
                item={item}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
