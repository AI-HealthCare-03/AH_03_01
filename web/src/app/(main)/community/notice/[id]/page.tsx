"use client";

import { use } from "react";
import PostDetail from "@/components/community/PostDetail";

export default function NoticePostDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <PostDetail postId={Number(id)} />;
}
