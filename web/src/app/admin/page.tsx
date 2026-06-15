"use client";

import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api/admin";

function StatCard({ label, value, sub }: { label: string; value: number; sub?: string }) {
  return (
    <div className="bg-[#1a1a1a] border border-white/10 rounded-[14px] p-5">
      <p className="text-white/50 text-xs mb-2">{label}</p>
      <p className="text-2xl font-black text-white">{value.toLocaleString()}</p>
      {sub && <p className="text-xs text-white/40 mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: adminApi.getStats,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="h-24 bg-white/5 animate-pulse rounded-[14px]" />
        ))}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-black text-white">대시보드</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        <StatCard label="전체 회원" value={stats.total_users} />
        <StatCard label="활성 회원" value={stats.active_users} sub={`${stats.total_users > 0 ? Math.round((stats.active_users / stats.total_users) * 100) : 0}%`} />
        <StatCard label="전체 챌린지" value={stats.total_challenges} />
        <StatCard label="진행 중 챌린지" value={stats.active_challenges} />
        <StatCard label="전체 게시글" value={stats.total_posts} />
        <StatCard label="미답변 문의" value={stats.pending_inquiries} />
        <StatCard label="처리 대기 신고" value={stats.pending_reports} />
      </div>
    </div>
  );
}
