"use client";

import { use } from "react";
import PostDetail from "@/components/community/PostDetail";

export default function PostDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <PostDetail postId={Number(id)} />;
}
