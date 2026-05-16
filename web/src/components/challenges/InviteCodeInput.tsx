"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";

/* =========================================
   초대 코드 입력 컴포넌트
   ========================================= */

interface InviteCodeInputProps {
  onSubmit: (code: string) => void;
  loading?: boolean;
}

export default function InviteCodeInput({
  onSubmit,
  loading = false,
}: InviteCodeInputProps) {
  const [code, setCode] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim()) {
      onSubmit(code.trim().toUpperCase());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2" noValidate>
      <label className="sr-only" htmlFor="invite-code-input">
        초대 코드 입력
      </label>
      <input
        id="invite-code-input"
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value.toUpperCase())}
        placeholder="초대 코드 입력 (예: ABC1234)"
        maxLength={12}
        className="flex-1 h-12 px-4 rounded-[12px] border border-border text-sm font-mono tracking-widest focus:outline-none focus:border-brand-black bg-white"
        autoCapitalize="characters"
        aria-label="초대 코드"
      />
      <Button
        type="submit"
        variant="secondary"
        size="md"
        loading={loading}
        disabled={!code.trim()}
      >
        참가
      </Button>
    </form>
  );
}
