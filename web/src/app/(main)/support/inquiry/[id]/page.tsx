"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteInquiry, getInquiry, updateInquiry } from "@/lib/api/support";
import { CATEGORY_LABEL, STATUS_LABEL, STATUS_STYLE } from "../_constants";

export default function InquiryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editError, setEditError] = useState("");

  const {
    data: inquiry,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["inquiry", id],
    queryFn: () => getInquiry(Number(id)),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      updateInquiry(Number(id), {
        title: editTitle.trim(),
        content: editContent.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiry", id] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      setEditError("");
      setIsEditing(false);
    },
    onError: () => {
      setEditError("저장에 실패했어요. 잠시 후 다시 시도해주세요.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteInquiry(Number(id)),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["inquiries"] });
      router.replace("/support/inquiry");
    },
  });

  function startEdit() {
    if (!inquiry) return;
    setEditTitle(inquiry.title);
    setEditContent(inquiry.content);
    setEditError("");
    setIsEditing(true);
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-12 bg-surface animate-pulse rounded-[12px]" />
        ))}
      </div>
    );
  }

  if (isError || !inquiry) {
    return (
      <p className="py-10 text-center text-sm text-text-tertiary">
        문의를 불러오지 못했어요.{" "}
        <Link href="/support/inquiry" className="underline">
          목록으로
        </Link>
      </p>
    );
  }

  const canEdit = inquiry.status === "PENDING";

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => (isEditing ? setIsEditing(false) : router.back())}
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          {isEditing ? "← 취소" : "← 목록"}
        </button>
        {canEdit && !isEditing && (
          <div className="flex gap-3">
            <button
              type="button"
              onClick={startEdit}
              className="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              수정
            </button>
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="text-sm text-status-error hover:opacity-70 transition-opacity disabled:opacity-40"
            >
              {deleteMutation.isPending ? "삭제 중…" : "삭제"}
            </button>
          </div>
        )}
      </div>

      {isEditing ? (
        /* 수정 폼 */
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-text-primary">제목</label>
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              maxLength={100}
              className="w-full px-3 py-2.5 border border-border rounded-[10px] text-sm outline-none focus:border-brand-black"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-text-primary">내용</label>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              maxLength={2000}
              rows={8}
              className="w-full px-3 py-2.5 border border-border rounded-[10px] text-sm outline-none focus:border-brand-black resize-none"
            />
            <p className="text-xs text-text-tertiary text-right">{editContent.length}/2000</p>
          </div>
          {editError && (
            <p className="text-sm text-status-error text-center">{editError}</p>
          )}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="flex-1 py-3 border border-border rounded-[12px] text-sm font-semibold text-text-secondary"
            >
              취소
            </button>
            <button
              type="button"
              onClick={() => updateMutation.mutate()}
              disabled={
                !editTitle.trim() || !editContent.trim() || updateMutation.isPending
              }
              className="flex-1 py-3 bg-brand-black text-white text-sm font-semibold rounded-[12px] disabled:opacity-40"
            >
              {updateMutation.isPending ? "저장 중…" : "저장"}
            </button>
          </div>
        </div>
      ) : (
        /* 문의 상세 */
        <div className="space-y-4">
          {/* 메타 */}
          <div className="space-y-2 pb-4 border-b border-border">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-text-tertiary bg-surface px-2 py-0.5 rounded-full">
                {CATEGORY_LABEL[inquiry.category]}
              </span>
              <span
                className={[
                  "px-2 py-0.5 rounded-full text-xs font-medium",
                  STATUS_STYLE[inquiry.status],
                ].join(" ")}
              >
                {STATUS_LABEL[inquiry.status]}
              </span>
            </div>
            <h1 className="text-base font-bold text-text-primary">{inquiry.title}</h1>
            <p className="text-xs text-text-tertiary">
              {new Date(inquiry.created_at).toLocaleDateString("ko-KR", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>

          {/* 내용 */}
          <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
            {inquiry.content}
          </p>

          {/* 첨부파일 */}
          {inquiry.attachment_url && (
            <a
              href={inquiry.attachment_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-brand-black underline"
            >
              📎 첨부파일 보기
            </a>
          )}

          {/* 답변 */}
          {inquiry.answer ? (
            <div className="p-4 bg-surface rounded-[12px] space-y-2 border border-border">
              <p className="text-xs font-semibold text-text-secondary">관리자 답변</p>
              <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
                {inquiry.answer.content}
              </p>
              <p className="text-xs text-text-tertiary">
                {new Date(inquiry.answer.created_at).toLocaleDateString("ko-KR", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            </div>
          ) : (
            <div className="p-4 bg-surface rounded-[12px] border border-border">
              <p className="text-sm text-text-tertiary text-center">
                아직 답변이 등록되지 않았어요.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
