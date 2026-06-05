"use client";

import { getWeekDays, KO_WEEKDAYS_MON, format, isToday, isSameDay, parseISO } from "@/lib/dateUtils";

/* =========================================
   이번 주 7칸 캘린더 (월~일)
   인증한 날: 노랑 채움
   ========================================= */

interface WeekStripProps {
  verifiedDates: string[];   /* "YYYY-MM-DD" 배열 — APPROVED */
  pendingDates?:  string[];  /* "YYYY-MM-DD" 배열 — AI 검증 중 */
}

export default function WeekStrip({ verifiedDates, pendingDates = [] }: WeekStripProps) {
  const weekDays = getWeekDays();

  return (
    <div>
      <p className="text-sm font-semibold text-text-primary mb-3">
        이번 주 달성 현황
      </p>
      <div className="flex gap-1.5 justify-between" role="list">
        {weekDays.map((day, idx) => {
          const isVerified = verifiedDates.some((d) => isSameDay(parseISO(d), day));
          const isPending  = !isVerified && pendingDates.some((d) => isSameDay(parseISO(d), day));
          const isCurrentDay = isToday(day);
          const label = isVerified ? "달성" : isPending ? "검증 중" : "미달성";

          return (
            <div
              key={idx}
              role="listitem"
              className="flex flex-col items-center gap-1.5"
              aria-label={`${format(day, "M월 d일")} ${label}`}
            >
              <span className="text-[10px] text-text-tertiary">
                {KO_WEEKDAYS_MON[idx]}
              </span>
              <div
                className={[
                  "w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold border-2",
                  isVerified
                    ? "bg-brand border-brand-black text-brand-black"
                    : isPending
                    ? "bg-status-info-bg border-status-info text-status-info"
                    : isCurrentDay
                    ? "border-brand-black bg-white text-text-primary"
                    : "border-border bg-white text-text-tertiary",
                ].join(" ")}
              >
                {isVerified ? "✓" : isPending ? "⏳" : format(day, "d")}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
