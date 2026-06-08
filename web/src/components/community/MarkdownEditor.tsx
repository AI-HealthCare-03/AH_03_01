"use client";

import { useRef } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

/** 마크다운 → HTML 변환 (XSS 방지: &<> 이스케이프 선처리) */
export function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^---$/gm, '<hr class="border-border my-3" />')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-bold mt-3 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold mt-4 mb-1">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-4 mb-2">$1</h1>')
    .replace(/^&gt; (.+)$/gm, '<blockquote class="border-l-4 border-border pl-3 my-1 text-text-secondary italic">$1</blockquote>')
    .replace(/^[-*] (.+)$/gm, '<li class="ml-5 list-disc">$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-5 list-decimal">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/~~(.+?)~~/g, "<s>$1</s>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="bg-surface px-1 rounded text-xs font-mono">$1</code>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="text-blue-600 underline" target="_blank" rel="noopener">$1</a>')
    .replace(/\n/g, "<br />");
}

const TOOLS = [
  { icon: "B", style: "font-bold", title: "굵게", before: "**", after: "**" },
  { icon: "I", style: "italic", title: "기울기", before: "*", after: "*" },
  { icon: "S", style: "line-through", title: "취소선", before: "~~", after: "~~" },
  { icon: "H1", style: "text-xs font-bold", title: "제목 1", before: "# ", after: "", plain: true },
  { icon: "H2", style: "text-xs font-bold", title: "제목 2", before: "## ", after: "", plain: true },
  { icon: "H3", style: "text-xs font-bold", title: "제목 3", before: "### ", after: "", plain: true },
  { icon: "</>", style: "font-mono text-xs", title: "인라인 코드", before: "`", after: "`" },
  { icon: "❝", style: "", title: "인용", before: "> ", after: "", plain: true },
  { icon: "•", style: "", title: "글머리 기호", before: "- ", after: "", plain: true },
  { icon: "1.", style: "text-xs", title: "번호 목록", before: "1. ", after: "", plain: true },
  { icon: "—", style: "", title: "구분선", before: "\n---\n", after: "", plain: true },
  { icon: "🔗", style: "", title: "링크", before: "[", after: "](url)" },
];

export default function MarkdownEditor({ value, onChange, placeholder }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function insert(before: string, after = "", plain = false) {
    const el = textareaRef.current;
    if (!el) return;
    const s = el.selectionStart;
    const e = el.selectionEnd;
    const sel = value.slice(s, e) || (plain ? "" : "텍스트");
    onChange(value.slice(0, s) + before + sel + after + value.slice(e));
    setTimeout(() => {
      el.focus();
      el.setSelectionRange(s + before.length, s + before.length + sel.length);
    }, 0);
  }

  return (
    <div className="border border-border rounded-[12px] overflow-hidden">
      {/* 툴바 */}
      <div className="flex items-center border-b border-border bg-surface px-2 gap-0.5 flex-wrap">
        {TOOLS.map(({ icon, style, title, before, after, plain = false }) => (
          <button key={title} type="button" title={title}
            onClick={() => insert(before, after, plain)}
            className={`px-2 py-1 text-sm text-text-secondary hover:text-text-primary hover:bg-white rounded transition-colors ${style}`}>
            {icon}
          </button>
        ))}
      </div>

      {/* 에디터 + 미리보기 분할 */}
      <div className="flex min-h-[250px]">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-1/2 px-4 py-3 text-sm text-text-primary resize-none outline-none border-r border-border"
        />
        <div
          className="w-1/2 px-4 py-3 text-sm text-text-primary leading-relaxed overflow-y-auto"
          dangerouslySetInnerHTML={{
            __html: value
              ? renderMarkdown(value)
              : '<span class="text-[var(--color-text-tertiary)]">미리보기가 여기에 표시됩니다.</span>',
          }}
        />
      </div>
    </div>
  );
}
