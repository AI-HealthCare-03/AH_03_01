"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPost, updatePost } from "@/lib/api/community";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";

export default function EditPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const postId = Number(id);
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const { data: post } = useQuery({
    queryKey: ["post", postId],
    queryFn: () => getPost(postId),
  });

  useEffect(() => {
    if (post) { setTitle(post.title); setContent(post.content); }
  }, [post]);

  const { mutate, isPending } = useMutation({
    mutationFn: () => updatePost(postId, { title, content }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["post", postId] });
      router.push(`/community/board/${postId}`);
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return showToast("제목과 내용을 입력해주세요.", "warning");
    mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h2 className="text-base font-bold text-text-primary">게시글 수정</h2>
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="제목을 입력하세요"
        className="px-4 py-2.5 text-sm border border-border rounded-[12px] outline-none focus:border-brand-black"
      />
      <MarkdownEditor value={content} onChange={setContent} placeholder="내용을 마크다운 형식으로 작성하세요." />
      <div className="flex justify-end gap-2">
        <button type="button" onClick={() => router.back()}
          className="px-4 py-2 text-sm border border-border rounded-[8px] hover:bg-surface transition-colors">
          취소
        </button>
        <button type="submit" disabled={isPending}
          className="px-4 py-2 text-sm font-semibold bg-brand-black text-white rounded-[8px] hover:opacity-80 disabled:opacity-50 transition-opacity">
          저장
        </button>
      </div>
    </form>
  );
}
