"use client";

import { useRef, useState } from "react";
import { uploadImage } from "@/lib/api/community";
import { API_BASE_URL } from "@/constants";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

/** 링크/이미지 URL 안전화: javascript:/data: 등 위험 스킴 차단(허용: http(s)·mailto·상대경로·앵커).
 *  허용 목록 방식이라 java\tscript: 같은 우회도 막힌다. 그 외는 "#" 로 무력화. */
function sanitizeUrl(url: string): string {
  const trimmed = url.trim();
  if (/^(https?:\/\/|mailto:)/i.test(trimmed)) return trimmed; // 절대 URL
  if (/^(\/|#|\.\.?\/)/.test(trimmed)) return trimmed; // 절대/상대 경로·앵커
  if (/^[\w.?=&%/-]+$/.test(trimmed)) return trimmed; // 스킴 없는 단순 경로(콜론 없음)
  return "#"; // javascript:, data:, vbscript: 등 차단
}

/** HTML 속성값에 들어갈 문자열의 따옴표를 이스케이프(속성 탈출 방지). */
function escapeAttr(value: string): string {
  return value.replace(/"/g, "&quot;");
}

/** 마크다운 → HTML 변환 (XSS 방지: &<> 이스케이프 선처리 + href/src 스킴 검증) */
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
    .replace(/!\[(.+?)\]\((.+?)\)/g, (_, alt, src) => {
      const cleaned = sanitizeUrl(src);
      const fullSrc = /^https?:\/\//i.test(cleaned)
        ? cleaned
        : `${API_BASE_URL}${cleaned.startsWith("/") ? "" : "/"}${cleaned}`;
      return `<img src="${escapeAttr(fullSrc)}" alt="${escapeAttr(alt)}" class="max-w-full rounded my-2" />`;
    })
    .replace(
      /\[(.+?)\]\((.+?)\)/g,
      (_, label, href) =>
        `<a href="${escapeAttr(sanitizeUrl(href))}" class="text-blue-600 underline" target="_blank" rel="noopener">${label}</a>`,
    )
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const url = await uploadImage(file);
      const pos = textareaRef.current?.selectionStart ?? value.length;
      onChange(value.slice(0, pos) + `![이미지](${url})` + value.slice(pos));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

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
        <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleImageUpload} />
        <button type="button" title="이미지 업로드" disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
          className="px-2 py-1 text-sm text-text-secondary hover:text-text-primary hover:bg-white rounded transition-colors disabled:opacity-40">
          {uploading ? "⏳" : "🖼"}
        </button>
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
