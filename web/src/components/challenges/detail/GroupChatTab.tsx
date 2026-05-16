"use client";

import { useState } from "react";
import { useVerifications } from "@/hooks/queries/useVerifications";
import { useCreateReaction } from "@/hooks/queries/useCreateReaction";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { format, parseISO } from "@/lib/dateUtils";
import type { ChallengeVerification } from "@/types/challenge";

/* =========================================
   그룹 챌린지 - 소통 탭 (인증 게시물 피드)
   좋아요/댓글 지원
   ========================================= */

interface GroupChatTabProps {
  challengeId: number;
}

function VerificationPost({ verification }: { verification: ChallengeVerification }) {
  const { showToast } = useToast();
  const likesMutation = useCreateReaction(verification.id);
  const [liked, setLiked] = useState(false);

  const handleLike = () => {
    setLiked(true);
    likesMutation.mutate(
      { type: "LIKE" },
      {
        onError: (err) => {
          setLiked(false);
          showToast(extractErrorMessage(err), "error");
        },
      }
    );
  };

  const statusLabel =
    verification.status === "APPROVED"
      ? "인증 완료"
      : verification.status === "PENDING"
      ? "검증 중"
      : "인증 실패";

  const statusColor =
    verification.status === "APPROVED"
      ? "text-status-success"
      : verification.status === "PENDING"
      ? "text-status-info"
      : "text-status-danger";

  return (
    <div className="bg-white border border-border rounded-[14px] p-4">
      {/* 헤더 */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-brand flex items-center justify-center text-sm font-bold">
          U
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-text-primary">
              유저{verification.user_id}
            </span>
            <span className={`text-xs font-semibold ${statusColor}`}>
              {statusLabel}
            </span>
          </div>
          <p className="text-xs text-text-tertiary">
            {format(parseISO(verification.created_at), "M월 d일 HH:mm")}
          </p>
        </div>
      </div>

      {/* 메모 */}
      {verification.memo && (
        <p className="text-sm text-text-secondary mb-3 leading-relaxed">
          {verification.memo}
        </p>
      )}

      {/* 인증 방식 */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={[
            "text-xs font-medium px-2 py-1 rounded-full",
            verification.method === "CHECK"
              ? "bg-status-success-bg text-status-success"
              : verification.method === "PHOTO"
              ? "bg-status-info-bg text-status-info"
              : "bg-surface text-text-secondary",
          ].join(" ")}
        >
          {verification.method === "CHECK"
            ? "✅ 체크 인증"
            : verification.method === "PHOTO"
            ? "📸 사진 인증"
            : "🛡️ 방지권"}
        </span>
      </div>

      {/* 액션 */}
      <div className="flex items-center gap-4 pt-2 border-t border-border">
        <button
          type="button"
          onClick={handleLike}
          disabled={liked || likesMutation.isPending}
          className={[
            "flex items-center gap-1.5 text-sm transition-colors",
            liked ? "text-status-danger" : "text-text-tertiary hover:text-status-danger",
          ].join(" ")}
          aria-label="좋아요"
        >
          <span aria-hidden="true">{liked ? "❤️" : "🤍"}</span>
          <span>좋아요</span>
        </button>
      </div>
    </div>
  );
}

export default function GroupChatTab({ challengeId }: GroupChatTabProps) {
  const { data, isLoading, error } = useVerifications(challengeId);
  const { showToast } = useToast();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-28 bg-surface rounded-[14px] animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm text-text-tertiary">
          인증 게시물을 불러오지 못했어요
        </p>
        <button
          type="button"
          onClick={() => showToast(extractErrorMessage(error), "error")}
          className="mt-2 text-xs text-text-tertiary underline"
        >
          다시 시도
        </button>
      </div>
    );
  }

  const items = data?.items ?? [];

  if (items.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-3xl mb-3" aria-hidden="true">
          📸
        </p>
        <p className="text-sm font-semibold text-text-secondary">
          아직 인증 게시물이 없어요
        </p>
        <p className="text-xs text-text-tertiary mt-1">
          오늘 인증하고 첫 번째 게시물을 남겨보세요!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((v) => (
        <VerificationPost key={v.id} verification={v} />
      ))}
    </div>
  );
}
