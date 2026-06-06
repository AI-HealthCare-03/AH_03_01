"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChallengeFeed } from "@/hooks/queries/useChallengeFeed";
import { useToggleLike } from "@/hooks/queries/useToggleLike";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import { format, parseISO } from "@/lib/dateUtils";
import type { VerificationFeedItem } from "@/types/challenge";

interface GroupChatTabProps {
  challengeId: number;
}

function FeedPost({
  post,
  challengeId,
  onCommentClick,
}: {
  post: VerificationFeedItem;
  challengeId: number;
  onCommentClick: (verificationId: number) => void;
}) {
  const { showToast } = useToast();
  const toggleLikeMutation = useToggleLike(challengeId);
  const [liked, setLiked] = useState(post.my_like);
  const [likeCount, setLikeCount] = useState(post.like_count);

  const handleLike = () => {
    const nextLiked = !liked;
    setLiked(nextLiked);
    setLikeCount((c) => c + (nextLiked ? 1 : -1));
    toggleLikeMutation.mutate(post.id, {
      onError: (err) => {
        setLiked(!nextLiked);
        setLikeCount((c) => c + (nextLiked ? -1 : 1));
        showToast(extractErrorMessage(err), "error");
      },
    });
  };

  const isTimer = post.method === "CHECK" && !!post.verified_duration_seconds;

  const statusLabel =
    isTimer ? "⏱️ 타이머 인증"
    : post.method === "CHECK" ? "✅ 체크 인증"
    : post.method === "PHOTO" ? "📸 사진 인증"
    : "🛡️ 방지권";

  const statusBgColor =
    isTimer ? "bg-surface text-text-secondary"
    : post.method === "CHECK" ? "bg-status-success-bg text-status-success"
    : post.method === "PHOTO" ? "bg-status-info-bg text-status-info"
    : "bg-surface text-text-secondary";

  return (
    <div className="bg-white border border-border rounded-[14px] p-4">
      {/* 헤더 */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-brand flex items-center justify-center text-sm font-bold shrink-0">
          {(post.user_nickname ?? "U")[0].toUpperCase()}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text-primary">
              {post.user_nickname ?? "유저"}
            </span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBgColor}`}>
              {statusLabel}
            </span>
          </div>
          <p className="text-xs text-text-tertiary">
            {format(parseISO(post.created_at), "M월 d일 HH:mm")}
          </p>
        </div>
      </div>

      {/* 사진 */}
      {post.photo_file_id && (
        <div className="mb-3 rounded-[10px] overflow-hidden bg-surface aspect-video flex items-center justify-center">
          <PhotoPreview fileId={post.photo_file_id} />
        </div>
      )}

      {/* caption */}
      {post.caption && (
        <p className="text-sm text-text-primary leading-relaxed mb-3">
          {post.caption}
        </p>
      )}

      {/* 액션 */}
      <div className="flex items-center gap-4 pt-2 border-t border-border">
        <button
          type="button"
          onClick={handleLike}
          disabled={toggleLikeMutation.isPending}
          className={[
            "flex items-center gap-1.5 text-sm transition-colors",
            liked ? "text-status-danger" : "text-text-tertiary hover:text-status-danger",
          ].join(" ")}
          aria-label={liked ? "좋아요 취소" : "좋아요"}
        >
          <span className="text-base" aria-hidden="true">{liked ? "❤️" : "🤍"}</span>
          {likeCount > 0 && (
            <span className="text-xs">{likeCount}</span>
          )}
        </button>
        <button
          type="button"
          onClick={() => onCommentClick(post.id)}
          className="flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-primary transition-colors"
          aria-label="댓글"
        >
          <span className="text-base" aria-hidden="true">💬</span>
          {post.comment_count > 0 && (
            <span className="text-xs">{post.comment_count}</span>
          )}
        </button>
      </div>
    </div>
  );
}

function PhotoPreview({ fileId }: { fileId: number }) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    import("@/lib/api/client").then(({ default: apiClient }) => {
      apiClient
        .get(`/api/v1/files/${fileId}`)
        .then(({ data }: { data: { access_url: string } }) => {
          const url = data.access_url.startsWith("http")
            ? data.access_url
            : `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}${data.access_url}`;
          setUrl(url);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    });
  }, [fileId]);

  if (loading) {
    return <div className="w-full h-full bg-surface animate-pulse" />;
  }
  if (!url) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <span className="text-3xl" aria-hidden="true">📸</span>
      </div>
    );
  }
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img src={url} alt="인증 사진" className="w-full h-full object-cover" />
  );
}

export default function GroupChatTab({ challengeId }: GroupChatTabProps) {
  const { data, isLoading, error } = useChallengeFeed(challengeId);
  const { showToast } = useToast();
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-28 bg-surface rounded-[14px] animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm text-text-tertiary">인증 게시물을 불러오지 못했어요</p>
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
        <p className="text-3xl mb-3" aria-hidden="true">📸</p>
        <p className="text-sm font-semibold text-text-secondary">아직 인증 게시물이 없어요</p>
        <p className="text-xs text-text-tertiary mt-1">오늘 인증하고 첫 번째 게시물을 남겨보세요!</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((post) => (
        <FeedPost
          key={post.id}
          post={post}
          challengeId={challengeId}
          onCommentClick={(verificationId) =>
            router.push(`/challenges/${challengeId}/feed/${verificationId}`)
          }
        />
      ))}
    </div>
  );
}
