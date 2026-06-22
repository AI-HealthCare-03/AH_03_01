"use client";

/* =========================================
   맞춤 추천 챌린지 섹션
   - 데스크탑: 3컬럼 그리드
   - 모바일: 가로 스크롤 스냅
   ========================================= */

import { useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import { useChallenges } from "@/hooks/queries/useChallenges";
import { useJoinChallenge } from "@/hooks/queries/useJoinChallenge";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type {
  ChallengeRecommendationItem,
  RecommendationPriority,
} from "@/types/api";
import type { ChallengeCategory } from "@/types/challenge";

const DISEASE_LABEL: Record<string, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
};
const RISK_LABEL: Record<string, string> = {
  HIGH_RISK: "고위험",
  RISK: "위험",
  CAUTION: "주의",
  NORMAL: "정상",
};

function parseFriendlyReason(raw?: string | null): string {
  if (!raw) return "위험도 분석 기반 맞춤 추천이에요";
  const match = raw.match(/^(\w+)\s+위험도\s+(\w+)/);
  if (match) {
    const disease = DISEASE_LABEL[match[1]] ?? match[1];
    const risk = RISK_LABEL[match[2]] ?? match[2];
    return `${disease} ${risk} 개선에 도움이 되는 챌린지예요`;
  }
  return raw;
}

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

/* ── 그룹 챌린지 참여 모달 ──────────────────── */
function GroupChallengeModal({
  open,
  onClose,
  category,
  categoryLabel,
}: {
  open: boolean;
  onClose: () => void;
  category: ChallengeCategory;
  categoryLabel: string;
}) {
  const { data, isLoading } = useChallenges({
    scope: "GROUP",
    category,
    size: 20,
    enabled: open,
  });
  const { mutate: join, isPending } = useJoinChallenge();
  const { showToast } = useToast();
  /* COMPLETED/CANCELLED 제외 — RECRUITING(참여 가능) + ACTIVE(정원 마감) 모두 표시 */
  const groupChallenges = (data?.items ?? []).filter(
    (c) => c.status === "RECRUITING" || c.status === "ACTIVE"
  );

  return (
    <Modal open={open} onClose={onClose} title={`${categoryLabel} 챌린지`} maxWidth="sm">
      <div className="px-6 py-5 space-y-4">
        {/* 직접 만들기 */}
        <Link href="/challenges/new" onClick={onClose}>
          <Button variant="primary" fullWidth>
            + 챌린지 만들기
          </Button>
        </Link>

        <div className="flex items-center gap-3 pt-3">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-text-tertiary">또는 그룹 참여</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* 그룹 챌린지 목록 */}
        {isLoading ? (
          <div className="space-y-2">
            {[0, 1].map((i) => (
              <div
                key={i}
                className="h-14 bg-surface rounded-xl animate-pulse"
              />
            ))}
          </div>
        ) : groupChallenges.length === 0 ? (
          <p className="text-sm text-text-tertiary text-center py-3">
            현재 참여 가능한 그룹 챌린지가 없어요
          </p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {groupChallenges.map((c) => {
              const isFull = c.status === "ACTIVE";
              return (
                <div
                  key={c.id}
                  className="flex items-center justify-between gap-2 p-3 bg-surface rounded-xl"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <p className="text-sm font-semibold text-text-primary truncate">
                        {c.title}
                      </p>
                      {isFull && (
                        <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-surface border border-border text-text-tertiary">
                          마감
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-text-tertiary">
                      {c.start_date} ~ {c.end_date}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 text-xs"
                    disabled={isPending}
                    onClick={() =>
                      join(
                        { challengeId: c.id },
                        {
                          onSuccess: () => {
                            showToast("챌린지에 참여했어요!", "success");
                            onClose();
                          },
                          onError: (err) => {
                            showToast(extractErrorMessage(err), "error");
                          },
                        }
                      )
                    }
                  >
                    참여하기
                  </Button>
                </div>
              );
            })}
          </div>
        )}

        <button
          type="button"
          className="w-full py-2 text-xs text-text-tertiary hover:text-text-primary transition-colors"
          onClick={onClose}
        >
          닫기
        </button>
      </div>
    </Modal>
  );
}

function RecommendationCard({ item }: { item: ChallengeRecommendationItem }) {
  const [modalOpen, setModalOpen] = useState(false);
  const priority = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.RECOMMENDED;
  const rewardLabel = `${item.reward_points ?? 200}P`;
  const categoryLabel = CATEGORY_CONFIG[item.category]?.label ?? item.title;

  return (
    <>
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
            {categoryLabel}
          </p>
          <p className="text-xs text-text-tertiary leading-relaxed line-clamp-2">
            {parseFriendlyReason(item.reason)}
          </p>
        </div>

        {/* 시작 버튼 */}
        <div className="mt-auto">
          <Button
            variant="outline"
            size="sm"
            fullWidth
            className="text-xs"
            aria-label={`${categoryLabel} 챌린지 시작하기`}
            onClick={() => setModalOpen(true)}
          >
            시작하기
          </Button>
        </div>
      </div>

      <GroupChallengeModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        category={item.category as ChallengeCategory}
        categoryLabel={categoryLabel}
      />
    </>
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
