"use client";

/* =========================================
   홈 대시보드 페이지
   와이어프레임 18-H01 (데스크탑) / 19-H01 (모바일)
   ========================================= */

import { format } from "date-fns";
import WelcomeBanner from "@/components/home/WelcomeBanner";
import QuickEntryGrid from "@/components/home/QuickEntryGrid";
import RiskSummary from "@/components/home/RiskSummary";
import RecommendationList from "@/components/home/RecommendationList";
import RecentMetricsGrid from "@/components/home/RecentMetricsGrid";
import { useMe } from "@/hooks/queries/useMe";
import { useMyPet } from "@/hooks/queries/useMyPet";
import { useMyActiveChallenges } from "@/hooks/queries/useMyActiveChallenges";
import { useLatestPredictions } from "@/hooks/queries/useLatestPredictions";
import { useChallengeRecommendations } from "@/hooks/queries/useChallengeRecommendations";
import { useAttendanceMonth } from "@/hooks/queries/useAttendanceMonth";
import { useHealthProfile } from "@/hooks/queries/useHealthProfile";
import { useMetricStat } from "@/hooks/queries/useMetricStat";

export default function HomePage() {
  const today = new Date();
  const currentMonth = format(today, "yyyy-MM");

  /* 데이터 훅 */
  const { data: me, isLoading: meLoading } = useMe();
  const { data: pet, isLoading: petLoading } = useMyPet();
  const { data: challengeData, isLoading: challengeLoading } =
    useMyActiveChallenges(5);
  const { data: predictions, isLoading: predictionsLoading } =
    useLatestPredictions();
  const { data: attendance, isLoading: attendanceLoading } =
    useAttendanceMonth(currentMonth);
  const { data: healthProfile, isLoading: profileLoading } = useHealthProfile();
  const { data: bpStat, isLoading: bpLoading } = useMetricStat("blood_pressure");
  const { data: fgStat, isLoading: fgLoading } = useMetricStat(
    "blood_glucose",
    "FASTING"
  );
  /* 예측 기반 고혈압 predictionId 추출 */
  const predItems = predictions?.items ?? [];
  const hyperPred = predItems.find((p) => p.disease_type === "HYPERTENSION");
  const { data: recommendations, isLoading: recLoading } =
    useChallengeRecommendations(hyperPred?.id, 3);

  const challenges = challengeData?.items ?? [];
  const activeChallengeCount = challenges.length;
  /* 오늘 인증 필요한 챌린지는 서버 필드 없어 active 수로 대체 */
  const pendingChallengeCount = activeChallengeCount;

  /* 예측 마지막 갱신일 */
  const latestPredictionDate = predItems[0]?.created_at;

  const metricsLoading =
    profileLoading || bpLoading || fgLoading;

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-6 md:px-10 md:py-8 space-y-8">
      {/* 1. 인사 배너 */}
      <WelcomeBanner
        user={me}
        activeChallengeCount={activeChallengeCount}
        pendingChallengeCount={pendingChallengeCount}
        isLoading={meLoading || challengeLoading}
      />

      {/* 2. 3등분 빠른 진입 카드 */}
      <QuickEntryGrid
        pet={pet}
        challenges={challenges}
        petLoading={petLoading}
        attendance={attendance}
        attendanceLoading={attendanceLoading}
      />

      {/* 3. 질병 위험도 요약 */}
      <RiskSummary
        predictions={predItems}
        isLoading={predictionsLoading}
        updatedAt={latestPredictionDate}
      />

      {/* 4. 맞춤 추천 챌린지 */}
      <RecommendationList
        items={recommendations?.items ?? []}
        isLoading={recLoading}
        hasPrediction={predItems.length > 0}
      />

      {/* 5. 최근 측정 데이터 */}
      <RecentMetricsGrid
        healthProfile={healthProfile}
        bloodPressure={bpStat}
        fastingGlucose={fgStat}
        isLoading={metricsLoading}
      />
    </div>
  );
}
