"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AdminInquiryItem } from "@/lib/api/admin";

const STATUS_LABEL: Record<string, string> = { PENDING: "답변 대기", ANSWERED: "답변 완료" };
const STATUS_STYLE: Record<string, string> = {
  PENDING: "bg-yellow-900/40 text-yellow-400",
  ANSWERED: "bg-green-900/40 text-green-400",
};
const CATEGORY_LABEL: Record<string, string> = {
  SERVICE_INQUIRY: "서비스 문의",
  ACCOUNT_INQUIRY: "계정 문의",
  ERROR_REPORT: "오류 신고",
  SANCTIONS_INQUIRY: "제재 문의",
  ETC: "기타",
};

export default function AdminSupportPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [target, setTarget] = useState<AdminInquiryItem | null>(null);
  const [answer, setAnswer] = useState("");

  const { data: inquiries = [], isLoading } = useQuery({
    queryKey: ["admin", "inquiries", statusFilter],
    queryFn: () => adminApi.listInquiries({ limit: 50, status: statusFilter || undefined }),
    staleTime: 10_000,
  });

  const answerMutation = useMutation({
    mutationFn: ({ id, content }: { id: number; content: string }) =>
      adminApi.answerInquiry(id, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "inquiries"] });
      setTarget(null);
      setAnswer("");
    },
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-black text-white">고객 문의 관리</h1>

      {/* 필터 */}
      <div className="flex gap-2">
        {["", "PENDING", "ANSWERED"].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={[
              "px-3 py-1.5 rounded-full text-xs font-semibold transition-colors",
              statusFilter === s ? "bg-brand text-brand-black" : "bg-white/5 text-white/50 hover:bg-white/10",
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
                <th className="px-4 py-3 text-left font-medium">회원</th>
                <th className="px-4 py-3 text-left font-medium">제목</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">분류</th>
                <th className="px-4 py-3 text-left font-medium">상태</th>
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
              ) : inquiries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-white/30 text-sm">
                    문의가 없습니다.
                  </td>
                </tr>
              ) : (
                inquiries.map((inq) => (
                  <tr key={inq.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-white/50 text-xs">{inq.user_email}</td>
                    <td className="px-4 py-3 text-white/80 max-w-[180px] truncate">{inq.title}</td>
                    <td className="px-4 py-3 text-white/40 hidden md:table-cell text-xs">
                      {CATEGORY_LABEL[inq.category] ?? inq.category}
                    </td>
                    <td className="px-4 py-3">
                      <span className={["px-2 py-0.5 rounded-full text-xs", STATUS_STYLE[inq.status] ?? "bg-white/10 text-white/40"].join(" ")}>
                        {STATUS_LABEL[inq.status] ?? inq.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {inq.status === "PENDING" && (
                        <button
                          type="button"
                          onClick={() => setTarget(inq)}
                          className="text-xs text-brand hover:text-brand/80 transition-colors"
                        >
                          답변 작성
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

      {/* 답변 모달 */}
      {target && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1a1a1a] border border-white/10 rounded-[16px] w-full max-w-lg p-6 space-y-4">
            <h2 className="text-base font-bold text-white">답변 작성</h2>
            <p className="text-sm text-white/60 line-clamp-2">{target.title}</p>
            <div className="space-y-1.5">
              <label className="text-xs text-white/50">답변 내용</label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand resize-none"
                placeholder="답변 내용을 입력하세요"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => { setTarget(null); setAnswer(""); }}
                className="flex-1 py-2.5 border border-white/10 rounded-[10px] text-sm text-white/60"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => answerMutation.mutate({ id: target.id, content: answer })}
                disabled={!answer.trim() || answerMutation.isPending}
                className="flex-1 py-2.5 bg-brand text-brand-black text-sm font-semibold rounded-[10px] disabled:opacity-40"
              >
                {answerMutation.isPending ? "등록 중…" : "답변 등록"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
