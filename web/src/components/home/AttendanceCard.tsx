"use client";

/* =========================================
   홈 출석 카드 (B 카드) — 컴팩트 버전
   - 오늘 출석 여부, 연속 일수
   - 7칸 주간 캘린더
   - 출석 체크 버튼
   ========================================= */

import Link from "next/link";
import { format } from "date-fns";
import Button from "@/components/ui/Button";
import {
  getWeekDays,
  getWeekDaysCompact,
  isCheckedDate,
  isToday,
  isBefore,
  KO_WEEKDAYS_MON,
} from "@/lib/dateUtils";
import type { AttendanceMonthResponse } from "@/types/api";
import { useCheckInToday } from "@/hooks/queries/useCheckInToday";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { useContainerWidth } from "@/hooks/useContainerWidth";

interface AttendanceCardProps {
  data: AttendanceMonthResponse | undefined;
  isLoading: boolean;
}

export default function AttendanceCard({
  data,
  isLoading,
}: AttendanceCardProps) {
  const { showToast } = useToast();
  const checkIn = useCheckInToday();

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const todayStr = format(today, "yyyy-MM-dd");
  const checkedDates = data?.checked_dates ?? [];
  const isCheckedToday = checkedDates.includes(todayStr);
  const streak = data?.current_streak ?? 0;
  const nextBonusAt = data?.next_bonus_at ?? 7;
  const daysToBonus = nextBonusAt - streak;

  const weekDays = getWeekDays(today);

  const [calRef, calWidth] = useContainerWidth<HTMLDivElement>();
  // 7칸(w-7=28px × 7 + gap × 6 ≈ 220px) 미만이면 오늘 중심 5일 표시
  const displayDays = calWidth !== null && calWidth < 230 ? getWeekDaysCompact(today, 5) : weekDays;

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

  return (
    <article
      aria-label="오늘의 출석"
      className="bg-white rounded-[16px] border border-border p-5 flex flex-col gap-4 shadow-sm"
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden="true">🎁</span>
          <h2 className="text-base font-bold text-text-primary">오늘의 출석</h2>
        </div>
        {isCheckedToday && (
          <span className="text-xs font-medium text-[#2e7d32] bg-[#e8f5e9] px-2 py-0.5 rounded-full">
            완료 ✓
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <div className="h-8 w-24 bg-surface rounded animate-pulse" />
          <div className="h-10 w-full bg-surface rounded animate-pulse" />
        </div>
      ) : (
        <>
          {/* 상태 텍스트 + 연속 일수 */}
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs text-text-tertiary mb-0.5">
                {isCheckedToday ? "오늘 출석 완료 ✓" : "아직 출석 전이에요"}
              </p>
              <p className="text-3xl font-black text-brand-black">
                {streak}
                <span className="text-base font-semibold text-text-secondary ml-1">
                  일째
                </span>
              </p>
            </div>
            <p className="text-xs text-text-tertiary text-right">
              연속 출석 중
            </p>
          </div>

          {/* 주간 캘린더 */}
          <div ref={calRef} className="flex justify-between gap-1 overflow-hidden" aria-label="이번 주 출석 현황">
            {displayDays.map((day) => {
              const dayStr = format(day, "yyyy-MM-dd");
              const checked = isCheckedDate(day, checkedDates);
              const todayFlag = isToday(day);
              const pastUnChecked =
                isBefore(day, today) && !checked && !todayFlag;
              // 요일 레이블을 Date에서 직접 도출 (5일 슬라이스에서도 정확한 요일 표시)
              const weekdayIdx = (day.getDay() + 6) % 7; // 월=0 … 일=6

              return (
                <div
                  key={dayStr}
                  className="flex flex-col items-center gap-1 flex-1 min-w-0"
                  aria-label={`${KO_WEEKDAYS_MON[weekdayIdx]}요일 ${checked ? "출석" : "미출석"}`}
                >
                  <span className="text-[10px] text-text-tertiary">
                    {KO_WEEKDAYS_MON[weekdayIdx]}
                  </span>
                  <div
                    className={[
                      "w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-semibold transition-colors",
                      checked
                        ? "bg-brand text-brand-black"
                        : pastUnChecked
                        ? "bg-surface text-text-disabled"
                        : todayFlag
                        ? "border-2 border-brand-black text-brand-black font-bold"
                        : "bg-surface text-text-tertiary",
                    ].join(" ")}
                  >
                    {format(day, "d")}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 보너스 안내 */}
          {daysToBonus === 1 && !isCheckedToday && (
            <p className="text-xs text-[#856404] bg-[#fffbe6] rounded-[8px] px-3 py-2">
              내일 출석 시 +20P 보너스 🎉
            </p>
          )}

          {/* 출석 버튼 */}
          {!isCheckedToday ? (
            <Button
              variant="primary"
              size="sm"
              fullWidth
              loading={checkIn.isPending}
              onClick={handleCheckIn}
              aria-label="오늘 출석 체크하기, 10포인트 적립"
            >
              오늘 출석체크 (+10P)
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              fullWidth
              disabled
              aria-label="오늘 출석 완료"
            >
              내일 다시 만나요 🌱
            </Button>
          )}
        </>
      )}

      {/* 상세 링크 */}
      <div className="pt-2 border-t border-border">
        <Link
          href="/attendance"
          className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
        >
          출석 상세 →
        </Link>
      </div>
    </article>
  );
}
