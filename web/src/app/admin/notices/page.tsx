"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AdminNoticeItem } from "@/lib/api/admin";

interface NoticeForm { title: string; content: string; }
const EMPTY: NoticeForm = { title: "", content: "" };

export default function AdminNoticesPage() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<AdminNoticeItem | null>(null);
  const [form, setForm] = useState<NoticeForm>(EMPTY);
  const [showDeleted, setShowDeleted] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const { data: notices = [], isLoading } = useQuery({
    queryKey: ["admin", "notices", showDeleted],
    queryFn: () => adminApi.listNotices({ limit: 50, show_deleted: showDeleted }),
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: (data: NoticeForm) => adminApi.createNotice(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "notices"] }); setCreating(false); setForm(EMPTY); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<NoticeForm> }) => adminApi.updateNotice(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "notices"] }); setEditing(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteNotice,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "notices"] }),
  });

  function openCreate() { setForm(EMPTY); setCreating(true); setEditing(null); }
  function openEdit(n: AdminNoticeItem) { setForm({ title: n.title, content: n.content ?? "" }); setEditing(n); setCreating(false); }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-black text-white">공지사항 관리</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowDeleted((v) => !v)}
            className={`px-3 py-2 text-sm rounded-[10px] border transition-colors ${showDeleted ? "bg-white/10 border-white/20 text-white" : "border-white/10 text-white/40 hover:text-white/60"}`}
          >
            {showDeleted ? "전체 보기" : "삭제된 항목 보기"}
          </button>
          {!showDeleted && (
            <button
              type="button"
              onClick={openCreate}
              className="px-4 py-2 bg-brand text-brand-black text-sm font-semibold rounded-[10px]"
            >
              + 공지 등록
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 bg-white/5 animate-pulse rounded-[12px]" />
          ))
        ) : notices.length === 0 ? (
          <p className="py-10 text-center text-white/30 text-sm">등록된 공지사항이 없습니다.</p>
        ) : (
          notices.map((n) => (
            <div key={n.id} className={`bg-[#1a1a1a] border rounded-[12px] px-4 py-3 flex items-center gap-3 ${n.is_deleted ? "border-red-500/20 opacity-60" : "border-white/10"}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-white/90 truncate">{n.title}</p>
                  {n.is_deleted && <span className="shrink-0 text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded-full">삭제됨</span>}
                </div>
                <p className="text-xs text-white/40 mt-0.5">
                  {new Date(n.created_at).toLocaleDateString("ko-KR")}
                  {n.author_name && ` · ${n.author_name}`}
                </p>
              </div>
              {!n.is_deleted && (
                <div className="flex gap-3 shrink-0">
                  <button type="button" onClick={() => openEdit(n)} className="text-xs text-white/50 hover:text-white">수정</button>
                  <button
                    type="button"
                    onClick={() => setDeleteConfirmId(n.id)}
                    disabled={deleteMutation.isPending}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    삭제
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* 삭제 확인 모달 */}
      {deleteConfirmId !== null && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1a1a1a] border border-white/10 rounded-[16px] w-full max-w-sm p-6 space-y-4">
            <h2 className="text-base font-bold text-white">공지 삭제</h2>
            <p className="text-sm text-white/60">삭제된 공지사항은 복구할 수 없습니다. 계속하시겠습니까?</p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                className="flex-1 py-2.5 border border-white/10 rounded-[10px] text-sm text-white/60"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => { deleteMutation.mutate(deleteConfirmId); setDeleteConfirmId(null); }}
                className="flex-1 py-2.5 bg-red-600 text-white text-sm font-semibold rounded-[10px]"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 등록/수정 모달 */}
      {(creating || editing) && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1a1a1a] border border-white/10 rounded-[16px] w-full max-w-lg p-6 space-y-4">
            <h2 className="text-base font-bold text-white">{creating ? "공지 등록" : "공지 수정"}</h2>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs text-white/50">제목</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-white/50">내용</label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                  rows={6}
                  className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand resize-none"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => { setCreating(false); setEditing(null); }}
                className="flex-1 py-2.5 border border-white/10 rounded-[10px] text-sm text-white/60"
              >
                취소
              </button>
              <button
                type="button"
                disabled={!form.title.trim() || !form.content.trim()}
                onClick={() => {
                  if (creating) createMutation.mutate(form);
                  else if (editing) updateMutation.mutate({ id: editing.id, data: { title: form.title, content: form.content } });
                }}
                className="flex-1 py-2.5 bg-brand text-brand-black text-sm font-semibold rounded-[10px] disabled:opacity-40"
              >
                {creating ? "등록" : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
