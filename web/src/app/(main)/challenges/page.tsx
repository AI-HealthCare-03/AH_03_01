"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ChallengeCard from "@/components/challenges/ChallengeCard";
import ChallengeListTabs from "@/components/challenges/ChallengeListTabs";
import RecommendationList from "@/components/home/RecommendationList";
import { useChallenges } from "@/hooks/queries/useChallenges";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import Button from "@/components/ui/Button";

/* =========================================
   챌린지 메인 목록 (10-C01 / 15-C01)
   탭: ?tab=active|completed|recommended
   ========================================= */

type TabKey = "active" | "completed" | "recommended";

function ChallengeListContent() {
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") ?? "active") as TabKey;

  /* 진행중/완료 챌린지.
     "진행중" 탭은 ACTIVE(시작됨) + RECRUITING(그룹, 멤버 모집 중) 모두 포함. */
  const { data: activeData, isLoading: activeLoading } = useChallenges({
    mine: true,
    status: "ACTIVE",
    size: 20,
  });
  const { data: recruitingData, isLoading: recruitingLoading } = useChallenges({
    mine: true,
    status: "RECRUITING",
    size: 20,
  });
  const { data: completedData, isLoading: completedLoading } = useChallenges({
    mine: true,
    status: "COMPLETED",
    size: 20,
  });

  /* 추천 - latest hypertension prediction 기반 */
  const { data: predictionsData } = useLatestPredictions();
  const latestHypertension = predictionsData?.items.find(
    (p) => p.disease_type === "HYPERTENSION"
  );
  const latestPredictionId = latestHypertension?.id;
  const {
    data: recommendationData,
    isLoading: recLoading,
  } = useChallengeRecommendations(latestPredictionId, 6);

  const activeItems = [...(activeData?.items ?? []), ...(recruitingData?.items ?? [])];
  const completedItems = completedData?.items ?? [];
  const recommendationItems = recommendationData?.items ?? [];

  return (
    <div className="max-w-5xl mx-auto px-5 py-6 md:px-8">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-black text-text-primary">챌린지</h1>
        {/* 액션 버튼들 */}
        <div className="flex items-center gap-2">
          <Link href="/challenges/join">
            <Button variant="outline" size="sm">
              코드로 참가
            </Button>
          </Link>
          <Link href="/challenges/new">
            <Button variant="secondary" size="sm">
              + 만들기
            </Button>
          </Link>
        </div>
      </div>

      {/* 탭 */}
      <div className="mb-5">
        <ChallengeListTabs currentTab={tab} />
      </div>

      <div className="md:flex md:gap-6">
        {/* 메인 콘텐츠 */}
        <div className="flex-1 min-w-0">
          {/* 진행중 탭 */}
          {tab === "active" && (
            <>
              {activeLoading || recruitingLoading ? (
                <div className="space-y-3">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="h-36 bg-white rounded-[16px] border border-border animate-pulse"
                    />
                  ))}
                </div>
              ) : activeItems.length === 0 ? (
                <div className="py-16 text-center bg-white rounded-[16px] border border-dashed border-border">
                  <p className="text-4xl mb-4" aria-hidden="true">🎯</p>
                  <p className="text-base font-bold text-text-primary mb-2">
                    아직 챌린지가 없어요
                  </p>
                  <p className="text-sm text-text-secondary mb-6">
                    건강한 습관을 만들기 위한 첫 챌린지를 시작해 보세요!
                  </p>
                  <Link href="/challenges/new">
                    <Button variant="primary" size="md">
                      첫 챌린지 만들기
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0">
                  {activeItems.map((c) => (
                    <ChallengeCard key={c.id} challenge={c} />
                  ))}
                </div>
              )}
            </>
          )}

          {/* 완료 탭 */}
          {tab === "completed" && (
            <>
              {completedLoading ? (
                <div className="space-y-3">
                  {[0, 1].map((i) => (
                    <div
                      key={i}
                      className="h-32 bg-white rounded-[16px] border border-border animate-pulse"
                    />
                  ))}
                </div>
              ) : completedItems.length === 0 ? (
                <div className="py-12 text-center bg-white rounded-[16px] border border-dashed border-border">
                  <p className="text-3xl mb-3" aria-hidden="true">🏆</p>
                  <p className="text-sm font-semibold text-text-secondary">
                    완료된 챌린지가 없어요
                  </p>
                </div>
              ) : (
                <div className="space-y-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0">
                  {completedItems.map((c) => (
                    <ChallengeCard key={c.id} challenge={c} showCTA={false} />
                  ))}
                </div>
              )}
            </>
          )}

          {/* 추천 탭 */}
          {tab === "recommended" && (
            <RecommendationList
              items={recommendationItems}
              isLoading={recLoading}
              hasPrediction={!!latestPredictionId}
            />
          )}
        </div>

        {/* 데스크탑 우측: 위험도 기반 추천 (세로 1컬럼 dense 모드) */}
        {tab !== "recommended" && (
          <aside className="hidden md:block w-72 shrink-0">
            <div className="bg-white border border-border rounded-[16px] p-5 shadow-sm">
              <p className="text-sm font-bold text-text-primary mb-4">
                위험도 기반 추천
              </p>
              <RecommendationList
                items={recommendationItems.slice(0, 3)}
                isLoading={recLoading}
                hasPrediction={!!latestPredictionId}
                dense
                showHeader={false}
              />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export default function ChallengePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-5xl mx-auto px-5 py-6">
          <div className="h-8 bg-surface rounded animate-pulse mb-4 w-32" />
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-36 bg-white rounded-[16px] border border-border animate-pulse"
              />
            ))}
          </div>
        </div>
      }
    >
      <ChallengeListContent />
    </Suspense>
  );
}
