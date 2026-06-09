"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createReport } from "@/lib/api/community";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { ReportTargetType, ReportReason } from "@/types/community";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "ABUSE", label: "욕설/혐오표현" },
  { value: "MISINFORMATION", label: "허위정보" },
  { value: "PRIVACY", label: "개인정보 노출" },
  { value: "AD", label: "광고/스팸" },
  { value: "FRAUD", label: "금전 거래 유도" },
  { value: "ETC", label: "기타" },
];

interface ReportModalProps {
  targetType: ReportTargetType;
  targetId: number;
  onClose: () => void;
}

export default function ReportModal({ targetType, targetId, onClose }: ReportModalProps) {
  const { showToast } = useToast();
  const [selected, setSelected] = useState<ReportReason | null>(null);

  const { mutate: submit, isPending } = useMutation({
    mutationFn: () => createReport({ target_type: targetType, target_id: targetId, reason: selected! }),
    onSuccess: () => { showToast("신고가 접수되었습니다.", "success"); onClose(); },
    onError: (err) => { showToast(extractErrorMessage(err), "error"); onClose(); },
  });

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-50" onClick={onClose} aria-hidden="true" />
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-[16px] w-full max-w-sm p-5 shadow-xl">
          <h2 className="text-base font-bold text-text-primary mb-4">신고 사유 선택</h2>
          <div className="space-y-2 mb-5">
            {REASONS.map((r) => (
              <button
                key={r.value}
                type="button"
                onClick={() => setSelected(r.value)}
                className={[
                  "w-full text-left px-4 py-2.5 rounded-[10px] border text-sm transition-colors",
                  selected === r.value
                    ? "border-brand-black bg-surface font-semibold text-text-primary"
                    : "border-border text-text-secondary hover:border-brand-black",
                ].join(" ")}
              >
                {r.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 border border-border rounded-[10px] text-sm text-text-secondary">
              취소
            </button>
            <button
              type="button"
              onClick={() => selected && submit()}
              disabled={!selected || isPending}
              className="flex-1 py-2.5 bg-brand-black text-white rounded-[10px] text-sm font-semibold disabled:opacity-40"
            >
              신고하기
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
