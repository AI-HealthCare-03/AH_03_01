"use client";

import { ExternalLink, BookText } from "lucide-react";
import type { ChatSource } from "@/types/chat";

/* =========================================
   출처 리스트 컴포넌트
   - 문서 코드(source) → 한글 문서명 라벨로 표시
   - 같은 문서의 여러 청크는 dedup, 상위 3개 문서만 노출
   - 신뢰도(confidence)는 UI 비노출 (개발자 모델 튜닝 전용)
   ========================================= */

/* 문서 코드 → 사용자 노출용 문서명 */
const SOURCE_LABELS: Record<string, string> = {
  KSH2022: "고혈압 진료지침 제5판",
  KDA2025: "당뇨병 진료지침 2025",
  KSOLA2022: "이상지질혈증 진료지침 2022",
};

const MAX_SOURCES = 3;

interface ChatSourceListProps {
  sources: ChatSource[];
}

interface SourceDoc {
  key: string;
  label: string;
  url?: string;
}

/* sources 를 문서 단위로 dedup 후 상위 MAX_SOURCES 개 문서명만 추출 */
function toDocs(sources: ChatSource[]): SourceDoc[] {
  const seen = new Set<string>();
  const docs: SourceDoc[] = [];
  for (const s of sources) {
    const code = s.source ?? undefined;
    const label = code && SOURCE_LABELS[code];
    if (!label) continue;
    if (seen.has(code!)) continue;
    seen.add(code!);
    docs.push({ key: code!, label, url: s.url });
    if (docs.length >= MAX_SOURCES) break;
  }
  return docs;
}

export default function ChatSourceList({ sources }: ChatSourceListProps) {
  if (!sources || sources.length === 0) return null;

  const docs = toDocs(sources);
  if (docs.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {docs.map((doc) => (
        <div
          key={doc.key}
          className="flex items-center gap-1 bg-surface border border-border rounded-[6px] px-2 py-1 text-[11px]"
        >
          <BookText size={11} className="text-text-tertiary" aria-hidden="true" />
          {doc.url ? (
            <a
              href={doc.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-black underline underline-offset-2 flex items-center gap-1 hover:opacity-70"
            >
              {doc.label}
              <ExternalLink size={10} aria-hidden="true" />
            </a>
          ) : (
            <span className="text-text-secondary">{doc.label}</span>
          )}
        </div>
      ))}
    </div>
  );
}
