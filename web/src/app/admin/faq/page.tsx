"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type FAQItem } from "@/lib/api/admin";

const CATEGORIES = [
  { value: "ACCOUNT", label: "계정" },
  { value: "CHALLENGE", label: "챌린지" },
  { value: "HEALTH_DATA", label: "건강 데이터" },
  { value: "REWARD", label: "리워드" },
];

const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]));

interface FaqForm { question: string; answer: string; category: string; order: number; }
const EMPTY_FORM: FaqForm = { question: "", answer: "", category: "ACCOUNT", order: 0 };

export default function AdminFaqPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<FAQItem | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FaqForm>(EMPTY_FORM);
  const [showDeleted, setShowDeleted] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const { data: faqs = [], isLoading } = useQuery({
    queryKey: ["admin", "faqs", showDeleted],
    queryFn: () => adminApi.listFaqs({ show_deleted: showDeleted }),
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: (data: FaqForm) => adminApi.createFaq(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "faqs"] }); setCreating(false); setForm(EMPTY_FORM); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FaqForm> }) => adminApi.updateFaq(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "faqs"] }); setEditing(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteFaq,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "faqs"] }),
  });

  function openCreate() { setForm(EMPTY_FORM); setCreating(true); setEditing(null); }
  function openEdit(faq: FAQItem) {
    setForm({ question: faq.question, answer: faq.answer, category: faq.category, order: faq.order });
    setEditing(faq);
    setCreating(false);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-black text-white">FAQ 관리</h1>
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
              + FAQ 등록
            </button>
          )}
        </div>
      </div>

      {/* FAQ 목록 */}
      <div className="space-y-2">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-white/5 animate-pulse rounded-[12px]" />
          ))
        ) : faqs.length === 0 ? (
          <p className="py-10 text-center text-white/30 text-sm">등록된 FAQ가 없습니다.</p>
        ) : (
          faqs.map((faq) => (
            <div key={faq.id} className={`bg-[#1a1a1a] border rounded-[12px] px-4 py-3 flex items-start gap-3 ${faq.is_deleted ? "border-red-500/20 opacity-60" : "border-white/10"}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-full">
                    {CATEGORY_LABEL[faq.category] ?? faq.category}
                  </span>
                  <span className="text-xs text-white/30">순서 {faq.order}</span>
                  {faq.is_deleted && <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded-full">삭제됨</span>}
                </div>
                <p className="text-sm font-semibold text-white/90 truncate">{faq.question}</p>
                <p className="text-xs text-white/40 mt-0.5 line-clamp-1">{faq.answer}</p>
              </div>
              {!faq.is_deleted && (
                <div className="flex gap-3 shrink-0">
                  <button type="button" onClick={() => openEdit(faq)} className="text-xs text-white/50 hover:text-white">수정</button>
                  <button
                    type="button"
                    onClick={() => setDeleteConfirmId(faq.id)}
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
            <h2 className="text-base font-bold text-white">FAQ 삭제</h2>
            <p className="text-sm text-white/60">삭제된 FAQ는 복구할 수 없습니다. 계속하시겠습니까?</p>
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
            <h2 className="text-base font-bold text-white">{creating ? "FAQ 등록" : "FAQ 수정"}</h2>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs text-white/50">카테고리</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand"
                >
                  {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-white/50">질문</label>
                <input
                  type="text"
                  value={form.question}
                  onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))}
                  className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-white/50">답변</label>
                <textarea
                  value={form.answer}
                  onChange={(e) => setForm((f) => ({ ...f, answer: e.target.value }))}
                  rows={4}
                  className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand resize-none"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-white/50">순서</label>
                <input
                  type="number"
                  value={form.order}
                  onChange={(e) => setForm((f) => ({ ...f, order: Number(e.target.value) }))}
                  className="w-full px-3 py-2 bg-[#111] border border-white/10 rounded-[10px] text-sm text-white outline-none focus:border-brand"
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
                disabled={!form.question.trim() || !form.answer.trim()}
                onClick={() => {
                  if (creating) createMutation.mutate(form);
                  else if (editing) updateMutation.mutate({ id: editing.id, data: form });
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
