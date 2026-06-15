"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api/admin";

const STATUS_LABEL: Record<string, string> = {
  RECRUITING: "모집 중",
  ACTIVE: "진행 중",
  COMPLETED: "완료",
  CANCELLED: "취소",
};

const STATUS_COLOR: Record<string, string> = {
  RECRUITING: "bg-blue-900/50 text-blue-400",
  ACTIVE: "bg-green-900/50 text-green-400",
  COMPLETED: "bg-white/10 text-white/40",
  CANCELLED: "bg-red-900/30 text-red-400",
};

const SCOPE_LABEL: Record<string, string> = {
  PERSONAL: "개인",
  GROUP: "그룹",
};

export default function AdminChallengesPage() {
  const [statusFilter, setStatusFilter] = useState("");

  const { data: challenges = [], isLoading } = useQuery({
    queryKey: ["admin", "challenges", statusFilter],
    queryFn: () => adminApi.listChallenges({ limit: 50, status: statusFilter || undefined }),
    staleTime: 10_000,
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-black text-white">챌린지 관리</h1>

      {/* 필터 */}
      <div className="flex gap-2 flex-wrap">
        {["", "RECRUITING", "ACTIVE", "COMPLETED", "CANCELLED"].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={[
              "px-3 py-1.5 rounded-full text-xs font-semibold transition-colors",
              statusFilter === s
                ? "bg-brand text-brand-black"
                : "bg-white/5 text-white/50 hover:bg-white/10",
            ].join(" ")}
          >
            {s === "" ? "전체" : STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      <div className="bg-[#1a1a1a] border border-white/10 rounded-[14px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/40 text-xs">
                <th className="px-4 py-3 text-left font-medium">제목</th>
                <th className="px-4 py-3 text-left font-medium">유형</th>
                <th className="px-4 py-3 text-left font-medium">상태</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">참여자</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">기간</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td colSpan={5} className="px-4 py-3">
                      <div className="h-4 bg-white/5 animate-pulse rounded" />
                    </td>
                  </tr>
                ))
              ) : challenges.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-white/30 text-sm">
                    챌린지가 없습니다.
                  </td>
                </tr>
              ) : (
                challenges.map((c) => (
                  <tr key={c.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-white/80 max-w-[200px] truncate">{c.title}</td>
                    <td className="px-4 py-3 text-white/50">{SCOPE_LABEL[c.scope] ?? c.scope}</td>
                    <td className="px-4 py-3">
                      <span className={["px-2 py-0.5 rounded-full text-xs", STATUS_COLOR[c.status] ?? "bg-white/10 text-white/40"].join(" ")}>
                        {STATUS_LABEL[c.status] ?? c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-white/40 hidden md:table-cell">{c.participant_count}명</td>
                    <td className="px-4 py-3 text-white/40 hidden md:table-cell text-xs">
                      {c.start_date} ~ {c.end_date}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
