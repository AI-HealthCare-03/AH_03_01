import Link from "next/link";
import type { PostListItem } from "@/types/community";

export default function PostCard({ post, basePath = "/community/board" }: { post: PostListItem; basePath?: string }) {
  return (
    <Link
      href={`${basePath}/${post.id}`}
      className="block p-4 bg-white border border-border rounded-[12px] hover:shadow-sm transition-shadow"
    >
      <div className="flex items-center gap-1.5 mb-1">
        {post.is_pinned && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 bg-red-100 text-red-600 rounded">📌 고정</span>
        )}
        <p className="text-sm font-semibold text-text-primary truncate">{post.title}</p>
      </div>
      <p className="text-xs text-text-tertiary">
        {post.author_nickname ?? "익명"} · 조회 {post.view_count}
        {post.like_count > 0 && <span> · ❤️ {post.like_count}</span>}
        {post.comment_count > 0 && <span> · 💬 {post.comment_count}</span>}
        {" · "}{new Date(post.created_at).toLocaleDateString("ko-KR")}
      </p>
    </Link>
  );
}
