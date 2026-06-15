"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createInquiry } from "@/lib/api/support";
import { useToast } from "@/components/ui/Toast";

interface ReportSupportModalProps {
  onClose: () => void;
}

export default function ReportSupportModal({ onClose }: ReportSupportModalProps) {
  const { showToast } = useToast();
  const [content, setContent] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createInquiry({
        title: "불편사항 신고",
        content: content.trim(),
        category: "ERROR_REPORT",
      }),
    onSuccess: () => {
      showToast("신고가 접수되었습니다.", "success");
      onClose();
    },
    onError: () => {
      showToast("신고 접수에 실패했어요. 잠시 후 다시 시도해주세요.", "error");
    },
  });

  const canSubmit = content.trim().length > 0 && !isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    mutate();
  }

  return (
    <>
      {/* 딤 배경 */}
      <div
        className="fixed inset-0 bg-black/40 z-50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 모달 */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center px-4"
        onClick={onClose}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="report-modal-title"
          className="bg-white rounded-[16px] w-full max-w-sm p-5 shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 id="report-modal-title" className="text-base font-bold text-text-primary mb-1">불편사항 신고</h2>
          <p className="text-xs text-text-tertiary mb-4">
            서비스 이용 중 불편한 점을 알려주세요.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="report-content" className="text-sm font-semibold text-text-primary">내용</label>
              <textarea
                id="report-content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                maxLength={2000}
                rows={6}
                placeholder="불편한 점을 자세히 작성해주세요"
                className="w-full px-3 py-2.5 border border-border rounded-[10px] text-sm outline-none focus:border-brand-black resize-none"
              />
              <p className="text-xs text-text-tertiary text-right">
                {content.length}/2000
              </p>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 border border-border rounded-[10px] text-sm font-semibold text-text-secondary"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="flex-1 py-2.5 bg-brand-black text-white rounded-[10px] text-sm font-semibold disabled:opacity-40"
              >
                {isPending ? "접수 중…" : "신고하기"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
