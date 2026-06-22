"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AdminUserItem } from "@/lib/api/admin";

export default function AdminUsersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [banTarget, setBanTarget] = useState<AdminUserItem | null>(null);
  const [banReason, setBanReason] = useState("");
  const [unbanTarget, setUnbanTarget] = useState<AdminUserItem | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin", "users", query],
    queryFn: () => adminApi.listUsers({ limit: 50, search: query || undefined }),
    staleTime: 10_000,
  });

  const banMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => adminApi.banUser(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      setBanTarget(null);
      setBanReason("");
    },
  });

  const unbanMutation = useMutation({
    mutationFn: (id: string) => adminApi.unbanUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-black text-white">회원 관리</h1>

      {/* 검색 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && setQuery(search)}
          placeholder="이메일 · 닉네임 · 이름 검색"
          className="flex-1 px-3 py-2 bg-[#1a1a1a] border border-white/10 rounded-[10px] text-sm text-white placeholder:text-white/30 outline-none focus:border-brand"
        />
        <button
          type="button"
          onClick={() => setQuery(search)}
          className="px-4 py-2 bg-brand text-brand-black text-sm font-semibold rounded-[10px]"
        >
          검색
        </button>
      </div>

      {/* 테이블 */}
      <div className="bg-[#1a1a1a] border border-white/10 rounded-[14px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/40 text-xs">
                <th className="px-4 py-3 text-left font-medium">이메일</th>
                <th className="px-4 py-3 text-left font-medium">닉네임</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">가입일</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">마지막 접속</th>
                <th className="px-4 py-3 text-left font-medium">상태</th>
                <th className="px-4 py-3 text-right font-medium">관리</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="h-4 bg-white/5 animate-pulse rounded" />
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-white/30 text-sm">
                    검색 결과가 없습니다.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-white/80">{u.email}</td>
                    <td className="px-4 py-3 text-white/60">{u.nickname ?? u.name}</td>
                    <td className="px-4 py-3 text-white/40 hidden md:table-cell">
                      {new Date(u.created_at).toLocaleDateString("ko-KR")}
                    </td>
                    <td className="px-4 py-3 text-white/40 hidden md:table-cell">
                      {u.last_login ? new Date(u.last_login).toLocaleDateString("ko-KR") : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {u.is_banned ? (
                        <span className="px-2 py-0.5 bg-red-900/50 text-red-400 rounded-full text-xs">정지</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-green-900/50 text-green-400 rounded-full text-xs">정상</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {u.is_banned ? (
                        <button
                          type="button"
                          onClick={() => setUnbanTarget(u)}
                          disabled={unbanMutation.isPending}
                          className="text-xs text-white/50 hover:text-white transition-colors"
                        >
                          정지 해제
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setBanTarget(u)}
                          className="text-xs text-red-400 hover:text-red-300 transition-colors"
                        >
                          강퇴
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 정지 해제 확인 모달 */}
      {unbanTarget && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1a1a1a] border border-white/10 rounded-[16px] w-full max-w-sm p-6 space-y-4">
            <h2 className="text-base font-bold text-white">정지 해제</h2>
            <p className="text-sm text-white/60">
              <span className="text-white font-semibold">{unbanTarget.email}</span> 회원의 정지를 해제합니다. 계속하시겠습니까?
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setUnbanTarget(null)}
                className="flex-1 py-2.5 border border-white/10 rounded-[10px] text-sm text-white/60"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => { unbanMutation.mutate(unbanTarget.id); setUnbanTarget(null); }}
                disabled={unbanMutation.isPending}
                className="flex-1 py-2.5 bg-brand text-brand-black text-sm font-semibold rounded-[10px] disabled:opacity-40"
              >
                해제 확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 강퇴 모달 */}
      {banTarget && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1a1a1a] border border-white/10 rounded-[16px] w-full max-w-md p-6 space-y-4">
            <h2 className="text-base font-bold text-white">회원 강퇴</h2>
            <p className="text-sm text-white/60">
              <span className="text-white font-semibold">{banTarget.email}</span> 회원을 강퇴합니다.
            </p>
            <div className="space-y-1.5">
              <label className="text-xs text-white/50">강퇴 사유 (필수)</label>
              <textarea
                value={banReason}
                onChange={(e) => setBanReason(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand resize-none"
                placeholder="강퇴 사유를 입력하세요"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => { setBanTarget(null); setBanReason(""); }}
                className="flex-1 py-2.5 border border-white/10 rounded-[10px] text-sm text-white/60"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => banMutation.mutate({ id: banTarget.id, reason: banReason })}
                disabled={!banReason.trim() || banMutation.isPending}
                className="flex-1 py-2.5 bg-red-600 text-white text-sm font-semibold rounded-[10px] disabled:opacity-40"
              >
                {banMutation.isPending ? "처리 중…" : "강퇴 확인"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
