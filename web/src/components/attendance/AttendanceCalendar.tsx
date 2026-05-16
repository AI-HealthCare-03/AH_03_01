"use client";

/* =========================================
   월간 출석 캘린더 컴포넌트
   - 월 이동 시 month prop 업데이트
   - 출석일 노랑, 오늘 굵은 테두리
   ========================================= */

import { format } from "date-fns";
import {
  getMonthCalendarDays,
  isCheckedDate,
  isToday,
  isBefore,
  isSameDay,
  KO_WEEKDAYS_SUN,
} from "@/lib/dateUtils";

interface AttendanceCalendarProps {
  year: number;
  month: number;
  checkedDates: string[];
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export default function AttendanceCalendar({
  year,
  month,
  checkedDates,
  onPrevMonth,
  onNextMonth,
}: AttendanceCalendarProps) {
  const calDays = getMonthCalendarDays(year, month);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  /* 이번 달 날짜만 구분하기 위한 기준 */
  const lastDayOfMonth = new Date(year, month, 0);

  const isSameMonth = (d: Date) =>
    d.getFullYear() === year && d.getMonth() === month - 1;

  /* 이번 달 총 출석일 */
  const monthTotal = checkedDates.filter((d) => {
    const [y, m] = d.split("-").map(Number);
    return y === year && m === month;
  }).length;

  /* 출석률 */
  const daysInMonth = lastDayOfMonth.getDate();
  const attendanceRate =
    daysInMonth > 0 ? Math.round((monthTotal / daysInMonth) * 100) : 0;

  return (
    <div className="bg-white rounded-[16px] border border-border p-5 shadow-sm">
      {/* 월 이동 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <button
          type="button"
          onClick={onPrevMonth}
          className="w-9 h-9 rounded-full hover:bg-surface flex items-center justify-center text-text-secondary transition-colors"
          aria-label="이전 달"
        >
          ◀
        </button>
        <h2 className="text-base font-bold text-text-primary">
          {year}년 {month}월
        </h2>
        <button
          type="button"
          onClick={onNextMonth}
          className="w-9 h-9 rounded-full hover:bg-surface flex items-center justify-center text-text-secondary transition-colors"
          aria-label="다음 달"
          disabled={
            year > today.getFullYear() ||
            (year === today.getFullYear() && month >= today.getMonth() + 1)
          }
        >
          ▶
        </button>
      </div>

      {/* 요일 헤더 */}
      <div className="grid grid-cols-7 mb-2">
        {KO_WEEKDAYS_SUN.map((day) => (
          <div
            key={day}
            className="text-center text-[11px] font-semibold text-text-tertiary py-1"
          >
            {day}
          </div>
        ))}
      </div>

      {/* 날짜 그리드 */}
      <div className="grid grid-cols-7 gap-y-1" role="grid" aria-label={`${year}년 ${month}월 출석 캘린더`}>
        {calDays.map((day) => {
          const dayStr = format(day, "yyyy-MM-dd");
          const inMonth = isSameMonth(day);
          const checked = isCheckedDate(day, checkedDates);
          const todayFlag = isToday(day);
          const isFuture =
            !isBefore(day, today) && !isSameDay(day, today);
          const pastUnchecked =
            inMonth &&
            isBefore(day, today) &&
            !checked &&
            !todayFlag;

          return (
            <div
              key={dayStr}
              role="gridcell"
              aria-label={`${format(day, "M월 d일")} ${checked ? "출석" : todayFlag ? "오늘" : ""}`}
              className="flex items-center justify-center py-1"
            >
              <div
                className={[
                  "w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                  !inMonth ? "opacity-0 pointer-events-none" : "",
                  inMonth && checked
                    ? "bg-brand text-brand-black font-bold"
                    : inMonth && todayFlag
                    ? "border-2 border-brand-black text-brand-black font-bold"
                    : inMonth && pastUnchecked
                    ? "text-text-disabled"
                    : inMonth && isFuture
                    ? "text-text-tertiary"
                    : "text-text-primary",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {inMonth ? format(day, "d") : ""}
              </div>
            </div>
          );
        })}
      </div>

      {/* 월 통계 요약 */}
      <div className="mt-5 pt-4 border-t border-border grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-xs text-text-tertiary">총 출석</p>
          <p className="text-lg font-black text-brand-black">
            {monthTotal}
            <span className="text-xs font-normal text-text-tertiary ml-0.5">일</span>
          </p>
        </div>
        <div>
          <p className="text-xs text-text-tertiary">출석률</p>
          <p className="text-lg font-black text-brand-black">
            {attendanceRate}
            <span className="text-xs font-normal text-text-tertiary ml-0.5">%</span>
          </p>
        </div>
        <div>
          <p className="text-xs text-text-tertiary">이번 달 보상</p>
          <p className="text-lg font-black text-brand-black">
            {monthTotal * 10}
            <span className="text-xs font-normal text-text-tertiary ml-0.5">P</span>
          </p>
        </div>
      </div>

      {/* 보상 안내 카드 */}
      <div className="mt-4 p-4 bg-brand-light rounded-[12px]">
        <p className="text-xs font-bold text-brand-black mb-1">출석 보상 안내</p>
        <ul className="space-y-1 text-xs text-text-secondary">
          <li>• 매일 출석 시 <strong>+10P</strong></li>
          <li>• 7일 연속 출석 <strong>+20P 보너스</strong></li>
          <li>• 30일 연속 출석 <strong>+100P 보너스</strong></li>
        </ul>
      </div>
    </div>
  );
}
