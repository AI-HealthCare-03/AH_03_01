"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import ChallengeCard from "@/components/challenges/ChallengeCard";
import ChallengeListTabs from "@/components/challenges/ChallengeListTabs";
import RecommendationList from "@/components/home/RecommendationList";
import InviteCodeInput from "@/components/challenges/InviteCodeInput";
import { useChallenges } from "@/hooks/queries/useChallenges";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { useToast } from "@/components/ui/Toast";
import { joinChallengeByCode } from "@/lib/api/challenge";
import { extractErrorMessage } from "@/lib/api/client";
import Button from "@/components/ui/Button";

/* =========================================
   챌린지 메인 목록
   탭: ?tab=join|my|recommended
   ========================================= */

type TabKey = "join" | "my" | "recommended";
type MySubTab = "active" | "completed";
type SortKey = "start_date" | "end_date" | undefined;
type PeriodKey = "1w" | "1m" | undefined;

function ChallengeListContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tab = (searchParams.get("tab") ?? "join") as TabKey;

  /* 내 챌린지 서브탭 */
  const [mySubTab, setMySubTab] = useState<MySubTab>("active");

  /* 참여하기 탭 — 코드 입력 토글 */
  const [showCodeInput, setShowCodeInput] = useState(false);

  /* 필터/정렬 상태 (내 챌린지 탭용) */
  const [period, setPeriod] = useState<PeriodKey>(undefined);
  const [sortBy, setSortBy] = useState<SortKey>(undefined);

  /* 기간 필터 → from/to 계산 */
  const getDateRange = () => {
    const today = new Date();
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    if (period === "1w") {
      const to = new Date(today);
      to.setDate(today.getDate() + 7);
      return { from: fmt(today), to: fmt(to) };
    }
    if (period === "1m") {
      const to = new Date(today);
      to.setMonth(today.getMonth() + 1);
      return { from: fmt(today), to: fmt(to) };
    }
    return { from: undefined, to: undefined };
  };
  const { from, to } = getDateRange();

  /* 내 챌린지 — 진행중(ACTIVE + RECRUITING) */
  const { data: activeData, isLoading: activeLoading } = useChallenges({
    mine: true, status: "ACTIVE", size: 20, from, to, sortBy,
    enabled: tab === "my",
  });
  const { data: recruitingData, isLoading: recruitingLoading } = useChallenges({
    mine: true, status: "RECRUITING", size: 20, from, to, sortBy,
    enabled: tab === "my",
  });
  const { data: completedData, isLoading: completedLoading } = useChallenges({
    mine: true, status: "COMPLETED", size: 20, from, to, sortBy,
    enabled: tab === "my",
  });

  /* 참여하기 탭 — 공개 그룹 모집중 챌린지 */
  const { data: joinData, isLoading: joinLoading } = useChallenges({
    scope: "GROUP", status: "RECRUITING", visibility: "PUBLIC", size: 20,
    enabled: tab === "join",
  });

  const { showToast } = useToast();
  const joinMutation = useMutation({
    mutationFn: (code: string) => joinChallengeByCode(code),
    onSuccess: (res) => {
      showToast("챌린지 참가 신청이 완료됐어요", "success");
      router.push(`/challenges/${res.challenge_id}`);
    },
    onError: (err) => {
      showToast(extractErrorMessage(err), "error");
    },
  });

  /* 추천 */
  const { data: predictionsData } = useLatestPredictions();
  const latestHypertension = predictionsData?.items.find(
    (p) => p.disease_type === "HYPERTENSION"
  );
  const latestPredictionId = latestHypertension?.id;
  const { data: recommendationData, isLoading: recLoading } =
    useChallengeRecommendations(latestPredictionId, 6);

  const activeItems = [...(activeData?.items ?? []), ...(recruitingData?.items ?? [])];
  const completedItems = completedData?.items ?? [];
  const groupItems = joinData?.items ?? [];
  const recommendationItems = recommendationData?.items ?? [];

  return (
    <div className="max-w-5xl mx-auto px-5 py-6 md:px-8">
      {/* 페이지 헤더 */}
      <div className="mb-5">
        <h1 className="text-xl font-black text-text-primary">챌린지 시작하기</h1>
        <p className="text-sm text-text-tertiary mt-1">매일의 케어가 쌓이면 건강한 내일이 돼요. 챌린지로 시작해 보세요.</p>
      </div>

      {/* 메인 탭 */}
      <div className="mb-3">
        <ChallengeListTabs currentTab={tab} />
      </div>

      {/* 내 챌린지 서브탭 + 필터/정렬 */}
      {tab === "my" && (
        <div className="mb-4 space-y-3">
          {/* 서브탭 */}
          <div className="flex gap-2">
            {(["active", "completed"] as MySubTab[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setMySubTab(s)}
                className={[
                  "px-4 py-1.5 rounded-full text-sm font-semibold border transition-colors",
                  mySubTab === s
                    ? "bg-brand-black text-white border-brand-black"
                    : "bg-white text-text-secondary border-border hover:border-brand-black",
                ].join(" ")}
              >
                {s === "active" ? "진행중" : "완료"}
              </button>
            ))}
          </div>

          {/* 필터/정렬 */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1.5">
              {([undefined, "1w", "1m"] as PeriodKey[]).map((p) => (
                <button
                  key={String(p)}
                  type="button"
                  onClick={() => setPeriod(p === period ? undefined : p)}
                  className={[
                    "px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors",
                    period === p
                      ? "bg-brand-black text-white border-brand-black"
                      : "bg-white text-text-secondary border-border hover:border-brand-black",
                  ].join(" ")}
                >
                  {p === undefined ? "전체" : p === "1w" ? "1주일" : "1개월"}
                </button>
              ))}
            </div>
            <div className="w-px h-4 bg-border" />
            <div className="flex gap-1.5">
              {([undefined, "start_date", "end_date"] as SortKey[]).map((s) => (
                <button
                  key={String(s)}
                  type="button"
                  onClick={() => setSortBy(s === sortBy ? undefined : s)}
                  className={[
                    "px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors",
                    sortBy === s
                      ? "bg-brand-black text-white border-brand-black"
                      : "bg-white text-text-secondary border-border hover:border-brand-black",
                  ].join(" ")}
                >
                  {s === undefined ? "기본순" : s === "start_date" ? "시작 날짜순" : "마감 임박순"}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="md:flex md:gap-6">
        <div className="flex-1 min-w-0">

          {/* 참여하기 탭 */}
          {tab === "join" && (
            <div className="space-y-6">
              {/* 2열 카드 */}
              <div className="grid grid-cols-2 gap-3">
                {/* 챌린지 만들기 */}
                <Link href="/challenges/new" className="block">
                  <div className={
                    showCodeInput
                      ? "bg-white border-2 border-border rounded-[16px] p-5 shadow-sm flex flex-col gap-2 transition-colors h-full hover:border-brand"
                      : "bg-white border-2 border-border rounded-[16px] p-5 shadow-sm flex flex-col gap-2 transition-colors h-full hover:border-brand-black"
                  }>
                    <span className="text-2xl" aria-hidden="true">✨</span>
                    <p className="text-sm font-bold text-text-primary">챌린지 만들기</p>
                    <p className="text-xs text-text-tertiary">나만의 챌린지를 직접 만들어 보세요</p>
                  </div>
                </Link>

                {/* 코드로 참가 */}
                <button
                  type="button"
                  onClick={() => setShowCodeInput((v) => !v)}
                  className={[
                    "bg-white border-2 rounded-[16px] p-5 shadow-sm flex flex-col gap-2 text-left w-full hover:border-brand-black transition-colors",
                    showCodeInput ? "border-brand-black" : "border-border",
                  ].join(" ")}
                >
                  <span className="text-2xl" aria-hidden="true">🔑</span>
                  <p className="text-sm font-bold text-text-primary">코드로 참가</p>
                  <p className="text-xs text-text-tertiary">초대 코드로 그룹 챌린지에 참가하세요</p>
                </button>
              </div>

              {/* 초대 코드 입력 (토글) */}
              {showCodeInput && (
                <div className="bg-white border border-border rounded-[16px] p-5 shadow-sm">
                  <p className="text-sm font-bold text-text-primary mb-3">초대 코드 입력</p>
                  <InviteCodeInput onSubmit={(code) => joinMutation.mutate(code)} />
                  <p className="text-xs text-text-tertiary mt-3">
                    초대 링크를 받았다면 링크를 직접 클릭하면 자동으로 참가 화면이 열려요
                  </p>
                </div>
              )}

              {/* 참가 가능한 그룹 챌린지 */}
              <div>
                <p className="text-sm font-bold text-text-primary mb-3">참가 가능한 그룹 챌린지</p>
                {joinLoading ? (
                  <div className="space-y-3">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="h-32 bg-white rounded-[16px] border border-border animate-pulse" />
                    ))}
                  </div>
                ) : groupItems.length === 0 ? (
                  <div className="py-12 text-center bg-white rounded-[16px] border border-dashed border-border">
                    <p className="text-3xl mb-3" aria-hidden="true">👥</p>
                    <p className="text-sm font-semibold text-text-secondary">현재 참가 가능한 그룹 챌린지가 없어요</p>
                    <p className="text-xs text-text-tertiary mt-1">직접 그룹 챌린지를 만들어 보세요!</p>
                  </div>
                ) : (
                  <div className="space-y-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0">
                    {groupItems.map((c) => (
                      <ChallengeCard key={c.id} challenge={c} showCTA={false} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 내 챌린지 탭 */}
          {tab === "my" && mySubTab === "active" && (
            <>
              {activeLoading || recruitingLoading ? (
                <div className="space-y-3">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-36 bg-white rounded-[16px] border border-border animate-pulse" />
                  ))}
                </div>
              ) : activeItems.length === 0 ? (
                <div className="py-16 text-center bg-white rounded-[16px] border border-dashed border-border">
                  <p className="text-4xl mb-4" aria-hidden="true">🎯</p>
                  <p className="text-base font-bold text-text-primary mb-2">아직 챌린지가 없어요</p>
                  <p className="text-sm text-text-secondary mb-6">건강한 습관을 만들기 위한 첫 챌린지를 시작해 보세요!</p>
                  <Link href="/challenges/new">
                    <Button variant="primary" size="md">첫 챌린지 만들기</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0">
                  {activeItems.map((c) => <ChallengeCard key={c.id} challenge={c} />)}
                </div>
              )}
            </>
          )}

          {tab === "my" && mySubTab === "completed" && (
            <>
              {completedLoading ? (
                <div className="space-y-3">
                  {[0, 1].map((i) => (
                    <div key={i} className="h-32 bg-white rounded-[16px] border border-border animate-pulse" />
                  ))}
                </div>
              ) : completedItems.length === 0 ? (
                <div className="py-12 text-center bg-white rounded-[16px] border border-dashed border-border">
                  <p className="text-3xl mb-3" aria-hidden="true">🏆</p>
                  <p className="text-sm font-semibold text-text-secondary">완료된 챌린지가 없어요</p>
                </div>
              ) : (
                <div className="space-y-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0">
                  {completedItems.map((c) => <ChallengeCard key={c.id} challenge={c} showCTA={false} />)}
                </div>
              )}
            </>
          )}

          {/* 추천 탭 */}
          {tab === "recommended" && (
            <div className="space-y-4">
              <div
                style={{ background: "rgba(249,224,0,0.07)", borderLeft: "3px solid #f9e000" }}
                className="rounded-r-[8px] px-4 py-2.5 flex items-center gap-2"
              >
                <span className="text-base" aria-hidden="true">✨</span>
                <p className="text-xs text-text-secondary">
                  내 건강 데이터와 위험도 예측 결과를 바탕으로 맞춤 챌린지를 선별했어요
                </p>
              </div>
              <RecommendationList
                items={recommendationItems}
                isLoading={recLoading}
                hasPrediction={!!latestPredictionId}
                showHeader={false}
              />
            </div>
          )}
        </div>

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
