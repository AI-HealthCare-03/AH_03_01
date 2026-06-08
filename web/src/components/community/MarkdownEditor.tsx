"use client";

import { useState } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

/** 기본 마크다운 → HTML 변환 (XSS 방지: &<> 이스케이프 선처리) */
export function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-bold mt-3 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold mt-4 mb-1">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-4 mb-2">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="bg-surface px-1 rounded text-xs font-mono">$1</code>')
    .replace(/\n/g, "<br />");
}

export default function MarkdownEditor({ value, onChange, placeholder }: Props) {
  const [preview, setPreview] = useState(false);

  return (
    <div className="border border-border rounded-[12px] overflow-hidden">
      <div className="flex border-b border-border bg-surface">
        {(["편집", "미리보기"] as const).map((label) => {
          const isPreview = label === "미리보기";
          return (
            <button
              key={label}
              type="button"
              onClick={() => setPreview(isPreview)}
              className={[
                "px-4 py-2 text-sm font-medium transition-colors",
                preview === isPreview
                  ? "bg-white text-text-primary border-b-2 border-brand-black -mb-px"
                  : "text-text-secondary hover:text-text-primary",
              ].join(" ")}
            >
              {label}
            </button>
          );
        })}
      </div>
      {preview ? (
        <div
          className="min-h-[200px] px-4 py-3 text-sm text-text-primary leading-relaxed"
          dangerouslySetInnerHTML={{
            __html: value
              ? renderMarkdown(value)
              : '<span class="text-[var(--color-text-tertiary)]">미리보기가 여기에 표시됩니다.</span>',
          }}
        />
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={10}
          className="w-full px-4 py-3 text-sm text-text-primary resize-y outline-none"
        />
      )}
    </div>
  );
}
