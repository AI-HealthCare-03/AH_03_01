"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchPointTransactions } from "@/lib/api/home";
import type { PointTransactionType } from "@/types/api";

/* =========================================
   포인트 적립/사용 거래 내역
   /mypage/points
   ========================================= */

type Tab = "ALL" | "EARN" | "SPEND";

const TABS: { id: Tab; label: string }[] = [
  { id: "ALL", label: "전체" },
  { id: "EARN", label: "적립" },
  { id: "SPEND", label: "사용" },
];

const PRESETS = [
  { label: "1주일", days: 7 },
  { label: "1개월", days: 30 },
  { label: "3개월", days: 90 },
];

const SOURCE_LABEL: Record<string, string> = {
  CHALLENGE_DAILY: "챌린지 일일 보상",
  CHALLENGE_PERIOD: "챌린지 기간 완수",
  CHALLENGE_GROUP: "그룹 챌린지",
  CHALLENGE_WEEKLY_RANK: "주간 랭킹",
  ATTENDANCE_DAILY: "출석",
  ATTENDANCE_BONUS: "출석 보너스",
  QUIZ: "퀴즈",
  STORE_PURCHASE: "상점 구매",
  PET_INTERACTION: "펫 상호작용",
  REFUND: "환불",
  ETC: "기타",
};

function toDateStr(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export default function PointsPage() {
  const [tab, setTab] = useState<Tab>("ALL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["point-transactions", tab, startDate, endDate],
    queryFn: () =>
      fetchPointTransactions({
        ...(tab !== "ALL" && { type: tab as PointTransactionType }),
        ...(startDate && { from: startDate }),
        ...(endDate && { to: endDate }),
      }),
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    staleTime: 0,
  });

  const balance = data?.balance ?? 0;
  const transactions = data?.transactions ?? [];

  const handlePreset = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days + 1);
    setStartDate(toDateStr(start));
    setEndDate(toDateStr(end));
  };

  const handleReset = () => {
    setStartDate("");
    setEndDate("");
  };

  const hasFilter = startDate || endDate;

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div>
        <Link
          href="/mypage"
          className="text-sm text-text-tertiary hover:text-text-secondary inline-block mb-3"
        >
          ← 마이페이지
        </Link>
        <h1 className="text-xl font-black text-text-primary">포인트 내역</h1>
      </div>

      {/* 잔액 */}
      <div className="bg-white border border-border rounded-[16px] p-5 shadow-sm flex items-end justify-between">
        <div>
          <p className="text-xs text-text-tertiary mb-1">현재 잔액</p>
          <p className="text-2xl font-black text-text-primary">
            {balance.toLocaleString()}{" "}
            <span className="text-base font-bold text-text-tertiary">P</span>
          </p>
        </div>
        <Link
          href="/pets/store"
          className="text-xs font-semibold text-brand-black bg-brand rounded-[10px] px-3 py-2"
        >
          상점 가기 →
        </Link>
      </div>

      {/* 탭 */}
      <div className="flex gap-2 overflow-x-auto" role="tablist">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={[
              "px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-colors",
              tab === id
                ? "bg-brand-black text-white"
                : "bg-surface text-text-secondary hover:bg-border",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 기간 필터 */}
      <div className="bg-white border border-border rounded-[16px] p-4 space-y-3">
        <p className="text-xs font-semibold text-text-secondary">기간 설정</p>

        {/* 프리셋 버튼 */}
        <div className="flex items-center gap-2">
          {PRESETS.map(({ label, days }) => (
            <button
              key={label}
              onClick={() => handlePreset(days)}
              className="px-3 py-1.5 rounded-full text-xs font-semibold bg-surface text-text-secondary hover:bg-border transition-colors"
            >
              {label}
            </button>
          ))}
          {hasFilter && (
            <button
              onClick={handleReset}
              className="ml-auto px-3 py-1.5 rounded-full text-xs font-semibold text-status-error hover:bg-red-50 transition-colors"
            >
              초기화
            </button>
          )}
        </div>

        {/* 날짜 직접 입력 */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            max={endDate || toDateStr(new Date())}
            className="flex-1 text-sm border border-border rounded-[10px] px-3 py-2 text-text-primary focus:outline-none focus:border-brand-black"
          />
          <span className="text-xs text-text-tertiary shrink-0">~</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            min={startDate}
            max={toDateStr(new Date())}
            className="flex-1 text-sm border border-border rounded-[10px] px-3 py-2 text-text-primary focus:outline-none focus:border-brand-black"
          />
        </div>
      </div>

      {/* 거래 내역 */}
      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 bg-surface animate-pulse rounded-[12px]"
            />
          ))}
        </div>
      ) : transactions.length === 0 ? (
        <div className="bg-white border border-dashed border-border rounded-[16px] py-12 text-center">
          <p className="text-3xl mb-2" aria-hidden="true">
            💸
          </p>
          <p className="text-sm text-text-secondary">
            {hasFilter
              ? "해당 기간의 거래 내역이 없어요"
              : "아직 거래 내역이 없어요"}
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {transactions.map((tx) => {
            const earn = tx.type === "EARN";
            const label = tx.source
              ? (SOURCE_LABEL[tx.source] ?? tx.source)
              : "기타";
            return (
              <li
                key={tx.id}
                className="bg-white border border-border rounded-[12px] px-4 py-3 flex items-start justify-between gap-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-text-primary truncate">
                    {tx.description || label}
                  </p>
                  <p className="text-[11px] text-text-tertiary mt-0.5">
                    {label} ·{" "}
                    {new Date(tx.created_at).toLocaleString("ko-KR", {
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p
                    className={`text-sm font-black ${earn ? "text-status-success" : "text-status-error"}`}
                  >
                    {earn ? "+" : "-"}
                    {tx.amount.toLocaleString()} P
                  </p>
                  {tx.balance_after !== undefined && (
                    <p className="text-[10px] text-text-tertiary mt-0.5">
                      잔액 {tx.balance_after.toLocaleString()}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
