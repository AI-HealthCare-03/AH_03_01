"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api/admin";

const REASON_LABEL: Record<string, string> = {
  SPAM: "스팸",
  ABUSE: "욕설/혐오",
  SEXUAL: "성적 콘텐츠",
  MISINFORMATION: "허위 정보",
  OTHER: "기타",
};

const TARGET_LABEL: Record<string, string> = {
  POST: "게시글",
  COMMENT: "댓글",
  VERIFICATION: "인증",
  CHALLENGE_PARTICIPANT: "챌린지 참여자",
};

export default function AdminCommunityPage() {
  const qc = useQueryClient();

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["admin", "reports"],
    queryFn: () => adminApi.listReports({ limit: 50 }),
    staleTime: 10_000,
  });

  const dismissMutation = useMutation({
    mutationFn: adminApi.dismissReport,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "reports"] }),
  });

  const deletePostMutation = useMutation({
    mutationFn: (id: number) => adminApi.deletePost(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "reports"] }),
  });

  const deleteCommentMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteComment(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "reports"] }),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-black text-white">커뮤니티 관리</h1>
      <p className="text-sm text-white/40">접수된 신고 목록입니다. 처리 후 신고를 닫거나 해당 게시글/댓글을 삭제할 수 있습니다.</p>

      <div className="bg-[#1a1a1a] border border-white/10 rounded-[14px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/40 text-xs">
                <th className="px-4 py-3 text-left font-medium">대상</th>
                <th className="px-4 py-3 text-left font-medium">ID</th>
                <th className="px-4 py-3 text-left font-medium">신고 사유</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">신고일</th>
                <th className="px-4 py-3 text-right font-medium">처리</th>
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
              ) : reports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-white/30 text-sm">
                    처리 대기 신고가 없습니다.
                  </td>
                </tr>
              ) : (
                reports.map((r) => (
                  <tr key={r.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-white/10 text-white/60 rounded-full text-xs">
                        {TARGET_LABEL[r.target_type] ?? r.target_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-white/50">#{r.target_id}</td>
                    <td className="px-4 py-3 text-white/70">{REASON_LABEL[r.reason] ?? r.reason}</td>
                    <td className="px-4 py-3 text-white/40 hidden md:table-cell text-xs">
                      {new Date(r.created_at).toLocaleDateString("ko-KR")}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        {(r.target_type === "POST" || r.target_type === "COMMENT") && (
                          <button
                            type="button"
                            onClick={() =>
                              r.target_type === "POST"
                                ? deletePostMutation.mutate(r.target_id)
                                : deleteCommentMutation.mutate(r.target_id)
                            }
                            className="text-xs text-red-400 hover:text-red-300 transition-colors"
                          >
                            삭제
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => dismissMutation.mutate(r.id)}
                          disabled={dismissMutation.isPending}
                          className="text-xs text-white/40 hover:text-white transition-colors"
                        >
                          신고 닫기
                        </button>
                      </div>
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
