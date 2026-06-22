"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import PostForm from "@/components/community/PostForm";
import type { PostCategory } from "@/types/community";

function NewPostContent() {
  const category = (useSearchParams().get("category") ?? "INFO") as PostCategory;
  return <PostForm category={category} />;
}

export default function NewPostPage() {
  return <Suspense><NewPostContent /></Suspense>;
}
