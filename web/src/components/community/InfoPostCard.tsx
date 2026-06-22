import Link from "next/link";
import type { PostListItem, InfoCategory } from "@/types/community";

const CATEGORY_LABEL: Record<InfoCategory, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "심혈관",
  LIFESTYLE: "생활습관",
};

const CATEGORY_COLOR: Record<InfoCategory, string> = {
  HYPERTENSION: "bg-red-100 text-red-700",
  DIABETES: "bg-blue-100 text-blue-700",
  CARDIOVASCULAR: "bg-purple-100 text-purple-700",
  LIFESTYLE: "bg-green-100 text-green-700",
};

export default function InfoPostCard({ post }: { post: PostListItem }) {
  return (
    <Link
      href={`/community/board/${post.id}`}
      className="block bg-white border border-border rounded-[16px] overflow-hidden hover:shadow-md transition-shadow"
    >
      {post.thumbnail_url ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={post.thumbnail_url}
            alt={post.title}
            className="w-full h-36 object-cover"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              (e.currentTarget.nextElementSibling as HTMLElement | null)?.removeAttribute("hidden");
            }}
          />
          <div className="w-full h-36 bg-gray-100" hidden />
        </>
      ) : (
        <div className="w-full h-36 bg-gray-100" />
      )}
      <div className="p-4 flex flex-col gap-2">
        {post.info_category && (
          <span
            className={`self-start text-[11px] font-semibold px-2 py-0.5 rounded-full ${CATEGORY_COLOR[post.info_category]}`}
          >
            {CATEGORY_LABEL[post.info_category]}
          </span>
        )}
        <p className="text-sm font-bold text-text-primary line-clamp-2 leading-snug">{post.title}</p>
        <p className="text-xs text-text-tertiary">
          {post.author_nickname ?? "익명"} · {new Date(post.created_at).toLocaleDateString("ko-KR")}
        </p>
        <p className="text-xs text-text-tertiary">
          조회 {post.view_count}
          {post.like_count > 0 && <span> · ❤️ {post.like_count}</span>}
          {post.comment_count > 0 && <span> · 💬 {post.comment_count}</span>}
        </p>
      </div>
    </Link>
  );
}
