"use client";

import { use } from "react";
import PostEdit from "@/components/community/PostEdit";

export default function EditPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <PostEdit postId={Number(id)} />;
}
