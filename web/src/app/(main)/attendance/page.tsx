"use client";

/* =========================================
   출석하기 상세 페이지 (18-A01)
   - 좌: 월간 캘린더 + 보상 안내
   - 우: 연속 일수 + 출석 버튼 + 통계 (데스크탑)
   - 모바일: 단일 컬럼 (사이드패널이 위로)
   ========================================= */

import { useState } from "react";
import Link from "next/link";
import AttendanceCalendar from "@/components/attendance/AttendanceCalendar";
import StreakSidePanel from "@/components/attendance/StreakSidePanel";
import { useAttendanceMonth } from "@/hooks/queries/useAttendanceMonth";
import { toMonthString } from "@/lib/dateUtils";

export default function AttendancePage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);

  const currentMonthStr = toMonthString(year, month);
  const { data, isLoading } = useAttendanceMonth(currentMonthStr);

  const handlePrevMonth = () => {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    /* 미래 월은 이동 불가 */
    const isCurrentOrPast =
      year < today.getFullYear() ||
      (year === today.getFullYear() && month < today.getMonth() + 1);
    if (!isCurrentOrPast) return;

    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
  };

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-6 md:px-10 md:py-8">
      {/* 뒤로가기 */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-text-tertiary hover:text-text-primary transition-colors mb-4"
      >
        ← 홈으로
      </Link>

      <h1 className="text-2xl font-black text-text-primary mb-6">
        출석 체크
      </h1>

      {/* 모바일: 단일 컬럼 (사이드패널 먼저) */}
      <div className="flex flex-col gap-6 md:hidden">
        <StreakSidePanel
          data={data}
          isLoading={isLoading}
          currentMonth={currentMonthStr}
        />
        <AttendanceCalendar
          year={year}
          month={month}
          checkedDates={data?.checked_dates ?? []}
          onPrevMonth={handlePrevMonth}
          onNextMonth={handleNextMonth}
        />
      </div>

      {/* 데스크탑: 좌우 레이아웃 */}
      <div className="hidden md:flex gap-6 items-start">
        {/* 좌: 캘린더 */}
        <div className="flex-1 min-w-0">
          <AttendanceCalendar
            year={year}
            month={month}
            checkedDates={data?.checked_dates ?? []}
            onPrevMonth={handlePrevMonth}
            onNextMonth={handleNextMonth}
          />
        </div>

        {/* 우: 사이드패널 */}
        <div className="w-[320px] shrink-0">
          <StreakSidePanel
            data={data}
            isLoading={isLoading}
            currentMonth={currentMonthStr}
          />
        </div>
      </div>
    </div>
  );
}
