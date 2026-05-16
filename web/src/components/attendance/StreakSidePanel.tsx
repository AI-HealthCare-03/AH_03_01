"use client";

/* =========================================
   출석 상세 우측 사이드패널
   - 연속 일수 카드, 출석 버튼
   - 최근 이력 배지, 이번달 통계
   ========================================= */

import Button from "@/components/ui/Button";
import { format } from "date-fns";
import { useCheckInToday } from "@/hooks/queries/useCheckInToday";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { AttendanceMonthResponse } from "@/types/api";

interface StreakSidePanelProps {
  data: AttendanceMonthResponse | undefined;
  isLoading: boolean;
  currentMonth: string;
}

export default function StreakSidePanel({
  data,
  isLoading,
}: StreakSidePanelProps) {
  const { showToast } = useToast();
  const checkIn = useCheckInToday();

  const today = new Date();
  const todayStr = format(today, "yyyy-MM-dd");
  const checkedDates = data?.checked_dates ?? [];
  const isCheckedToday = checkedDates.includes(todayStr);
  const streak = data?.current_streak ?? 0;
  const nextBonusAt = data?.next_bonus_at ?? 7;
  /* 백엔드 응답에 month_total 필드가 없으므로 checked_dates 길이로 계산 */
  const monthTotal = checkedDates.length;
  const daysInMonth = new Date(
    today.getFullYear(),
    today.getMonth() + 1,
    0
  ).getDate();
  const attendanceRate =
    daysInMonth > 0 ? Math.round((monthTotal / daysInMonth) * 100) : 0;
  const estimatedPoints = monthTotal * 10;
  const daysToBonus = nextBonusAt - streak;

  const handleCheckIn = async () => {
    try {
      const result = await checkIn.mutateAsync();
      const total = result.reward_point + result.bonus_point;
      if (result.bonus_point > 0) {
        showToast(`+${total}P 적립! 🔥 보너스 +${result.bonus_point}P`, "success");
      } else {
        showToast(`+${result.reward_point}P 적립!`, "success");
      }
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-36 bg-white rounded-[16px] border border-border animate-pulse" />
        <div className="h-12 bg-white rounded-[16px] border border-border animate-pulse" />
        <div className="h-28 bg-white rounded-[16px] border border-border animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 연속 일수 카드 */}
      <div className="bg-brand-black text-white rounded-[16px] p-6 text-center">
        <p className="text-xs text-white/60 mb-2">현재 연속 출석</p>
        <p className="text-5xl font-black text-brand leading-none">
          {streak}
        </p>
        <p className="text-sm text-white/80 mt-1 font-medium">일째</p>

        {/* 다음 보너스까지 */}
        {daysToBonus > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <p className="text-xs text-white/50">
              다음 보너스까지{" "}
              <span className="text-brand font-bold">{daysToBonus}일</span>
            </p>
          </div>
        )}
        {daysToBonus === 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <p className="text-xs text-brand font-bold">🎉 오늘 보너스 달성!</p>
          </div>
        )}
      </div>

      {/* 출석 버튼 */}
      {!isCheckedToday ? (
        <Button
          variant="primary"
          size="lg"
          fullWidth
          loading={checkIn.isPending}
          onClick={handleCheckIn}
          aria-label="오늘 출석 체크하기, 10포인트 적립"
        >
          오늘 출석체크 (+10P)
        </Button>
      ) : (
        <Button variant="outline" size="lg" fullWidth disabled>
          내일 다시 만나요 🌱
        </Button>
      )}

      {/* 최근 출석 이력 배지 */}
      <div className="bg-white rounded-[16px] border border-border p-4">
        <p className="text-xs font-semibold text-text-tertiary mb-3">
          최근 출석 기록
        </p>
        <div className="flex flex-wrap gap-2">
          {checkedDates
            .slice(-5)
            .reverse()
            .map((d) => (
              <span
                key={d}
                className="px-2.5 py-1 rounded-full bg-brand text-brand-black text-[11px] font-semibold"
              >
                {format(new Date(d), "M/d")}
              </span>
            ))}
          {checkedDates.length === 0 && (
            <p className="text-xs text-text-tertiary">
              아직 출석 기록이 없어요
            </p>
          )}
        </div>

        {/* 연속 달성 배지 */}
        {streak >= 7 && (
          <div className="mt-3 pt-3 border-t border-border">
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-brand text-brand-black text-xs font-bold">
              🔥 연속 {streak}일째 달성!
            </span>
          </div>
        )}
      </div>

      {/* 이번 달 통계 */}
      <div className="bg-white rounded-[16px] border border-border p-4">
        <p className="text-xs font-semibold text-text-tertiary mb-3">
          이번 달 통계
        </p>
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-text-secondary">총 출석</span>
            <span className="text-sm font-bold text-text-primary">
              {monthTotal}일
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-text-secondary">출석률</span>
            <span className="text-sm font-bold text-text-primary">
              {attendanceRate}%
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-text-secondary">획득 포인트</span>
            <span className="text-sm font-bold text-brand-black">
              +{estimatedPoints}P
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
