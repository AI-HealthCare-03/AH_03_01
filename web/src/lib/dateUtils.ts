/* =========================================
   날짜 관련 유틸 (date-fns 기반)
   D-day 계산, 주간 캘린더, 월간 캘린더
   ========================================= */

import {
  parseISO,
  differenceInCalendarDays,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  format,
  isSameDay,
  isBefore,
  isToday,
} from "date-fns";

/** 오늘 ~ end_date 남은 일수 (음수면 기간 종료) */
export function calcDDay(endDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return differenceInCalendarDays(parseISO(endDate), today);
}

/** D-day 라벨 문자열 */
export function dDayLabel(endDate: string): string {
  const days = calcDDay(endDate);
  if (days < 0) return "챌린지 종료";
  if (days === 0) return "오늘 마감";
  return `D-${days}`;
}

/** 이번 주 월~일 날짜 배열 */
export function getWeekDays(baseDate: Date = new Date()): Date[] {
  const start = startOfWeek(baseDate, { weekStartsOn: 1 }); /* 월요일 시작 */
  const end = endOfWeek(baseDate, { weekStartsOn: 1 });
  return eachDayOfInterval({ start, end });
}

/**
 * 이번 주 날짜 배열에서 baseDate를 중심으로 count개 날짜 반환.
 * 주 경계를 벗어나지 않으며, 남은 자리가 부족하면 반대쪽으로 채움.
 */
export function getWeekDaysCompact(baseDate: Date, count: number): Date[] {
  const week = getWeekDays(baseDate);
  const todayIdx = week.findIndex((d) => isSameDay(d, baseDate));
  const half = Math.floor(count / 2);
  let start = todayIdx - half;
  let end = start + count;
  if (start < 0) {
    start = 0;
    end = count;
  } else if (end > week.length) {
    end = week.length;
    start = end - count;
  }
  return week.slice(start, end);
}

/** 월간 캘린더 날짜 배열 (앞뒤 빈 칸 포함, 6주 기준) */
export function getMonthCalendarDays(year: number, month: number): Date[] {
  const firstDay = startOfMonth(new Date(year, month - 1, 1));
  const lastDay = endOfMonth(firstDay);
  const calStart = startOfWeek(firstDay, { weekStartsOn: 0 }); /* 일요일 시작 */
  const calEnd = endOfWeek(lastDay, { weekStartsOn: 0 });
  return eachDayOfInterval({ start: calStart, end: calEnd });
}

/** 날짜가 출석 완료 날짜 배열에 포함되는지 */
export function isCheckedDate(date: Date, checkedDates: string[]): boolean {
  return checkedDates.some((d) => isSameDay(parseISO(d), date));
}

/** 오늘인지 여부 */
export { isToday, isBefore, isSameDay, format, parseISO };

/** YYYY-MM 문자열로 포매팅 */
export function toMonthString(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

/** 한국어 요일 배열 (일~토) */
export const KO_WEEKDAYS_SUN = ["일", "월", "화", "수", "목", "금", "토"] as const;

/** 한국어 요일 배열 (월~일) */
export const KO_WEEKDAYS_MON = ["월", "화", "수", "목", "금", "토", "일"] as const;
