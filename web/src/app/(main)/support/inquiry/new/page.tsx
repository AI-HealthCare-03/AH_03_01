"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createInquiry } from "@/lib/api/support";
import type { InquiryCategory } from "@/types/support";

const CATEGORIES: { label: string; value: InquiryCategory }[] = [
  { label: "서비스 문의", value: "SERVICE_INQUIRY" },
  { label: "계정 문의", value: "ACCOUNT_INQUIRY" },
  { label: "오류 신고", value: "ERROR_REPORT" },
  { label: "제재 문의", value: "SANCTIONS_INQUIRY" },
  { label: "기타", value: "ETC" },
];

function NewInquiryForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const initialCategory =
    (searchParams.get("category") as InquiryCategory | null) ?? "SERVICE_INQUIRY";

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<InquiryCategory>(initialCategory);
  const [errorMsg, setErrorMsg] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createInquiry({ title: title.trim(), content: content.trim(), category }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      router.replace("/support/inquiry");
    },
    onError: () => {
      setErrorMsg("문의 제출에 실패했어요. 잠시 후 다시 시도해주세요.");
    },
  });

  const canSubmit = title.trim().length > 0 && content.trim().length > 0 && !isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    mutate();
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-black text-text-primary">문의 작성</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 카테고리 */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-text-primary">분류</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as InquiryCategory)}
            className="w-full px-3 py-2.5 border border-border rounded-[10px] text-sm bg-white outline-none focus:border-brand-black"
          >
            {CATEGORIES.map(({ label, value }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* 제목 */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-text-primary">제목</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={100}
            placeholder="제목을 입력해주세요"
            className="w-full px-3 py-2.5 border border-border rounded-[10px] text-sm outline-none focus:border-brand-black"
          />
        </div>

        {/* 내용 */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-text-primary">내용</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            maxLength={2000}
            rows={8}
            placeholder="문의 내용을 자세히 작성해주세요"
            className="w-full px-3 py-2.5 border border-border rounded-[10px] text-sm outline-none focus:border-brand-black resize-none"
          />
          <p className="text-xs text-text-tertiary text-right">{content.length}/2000</p>
        </div>

        {errorMsg && (
          <p className="text-sm text-status-error text-center">{errorMsg}</p>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex-1 py-3 border border-border rounded-[12px] text-sm font-semibold text-text-secondary"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={!canSubmit}
            className="flex-1 py-3 bg-brand-black text-white text-sm font-semibold rounded-[12px] disabled:opacity-40"
          >
            {isPending ? "제출 중…" : "제출하기"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function NewInquiryPage() {
  return (
    <Suspense fallback={<div className="h-48 bg-surface animate-pulse rounded-[12px]" />}>
      <NewInquiryForm />
    </Suspense>
  );
}
