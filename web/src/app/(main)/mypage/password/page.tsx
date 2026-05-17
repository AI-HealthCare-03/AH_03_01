"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { changeMyPassword } from "@/lib/api/user";
import { extractErrorMessage } from "@/lib/api/client";

/* =========================================
   마이페이지 - 비밀번호 변경
   ========================================= */

export default function PasswordChangePage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [current, setCurrent] = useState("");
  const [next1, setNext1] = useState("");
  const [next2, setNext2] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      changeMyPassword({
        current_password: current,
        new_password: next1,
      }),
    onSuccess: () => {
      showToast("비밀번호가 변경되었어요", "success");
      router.push("/mypage");
    },
    onError: (err) => {
      showToast(extractErrorMessage(err), "error");
    },
  });

  /* 클라이언트 사이드 검증 */
  const errors: string[] = [];
  if (next1 && next1.length < 8) errors.push("새 비밀번호는 8자 이상이어야 해요");
  if (next1 && next2 && next1 !== next2) errors.push("새 비밀번호가 일치하지 않아요");
  if (current && next1 && current === next1) errors.push("기존과 동일한 비밀번호는 사용할 수 없어요");

  const canSubmit =
    current.length >= 8 &&
    next1.length >= 8 &&
    next2.length >= 8 &&
    next1 === next2 &&
    current !== next1 &&
    !mutation.isPending;

  return (
    <div className="max-w-md mx-auto px-5 py-6 space-y-6">
      {/* 헤더 */}
      <div>
        <Link
          href="/mypage"
          className="text-sm text-text-tertiary hover:text-text-secondary inline-block mb-3"
        >
          ← 마이페이지
        </Link>
        <h1 className="text-xl font-black text-text-primary">비밀번호 변경</h1>
        <p className="text-sm text-text-secondary mt-1">
          안전한 비밀번호를 사용해 주세요. 8자 이상.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label
            htmlFor="cur"
            className="text-xs font-semibold text-text-secondary mb-1 block"
          >
            현재 비밀번호
          </label>
          <input
            id="cur"
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            className="w-full px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="new1"
            className="text-xs font-semibold text-text-secondary mb-1 block"
          >
            새 비밀번호
          </label>
          <input
            id="new1"
            type="password"
            value={next1}
            onChange={(e) => setNext1(e.target.value)}
            autoComplete="new-password"
            className="w-full px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="new2"
            className="text-xs font-semibold text-text-secondary mb-1 block"
          >
            새 비밀번호 확인
          </label>
          <input
            id="new2"
            type="password"
            value={next2}
            onChange={(e) => setNext2(e.target.value)}
            autoComplete="new-password"
            className="w-full px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
          />
        </div>
      </div>

      {errors.length > 0 && (
        <ul className="bg-status-error-bg rounded-[12px] px-4 py-3 space-y-1">
          {errors.map((err) => (
            <li key={err} className="text-xs text-status-error">
              · {err}
            </li>
          ))}
        </ul>
      )}

      <Button
        variant="primary"
        size="lg"
        fullWidth
        disabled={!canSubmit}
        loading={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        비밀번호 변경
      </Button>
    </div>
  );
}
