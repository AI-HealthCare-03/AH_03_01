"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getFAQs, listInquiries } from "@/lib/api/support";
import type { FAQCategory, InquiryStatus } from "@/types/support";

// ── 상수 ──────────────────────────────────────────────────────────────────────

const FAQ_CATEGORIES: { label: string; value: FAQCategory | "ALL" }[] = [
  { label: "전체", value: "ALL" },
  { label: "계정/회원", value: "ACCOUNT" },
  { label: "챌린지", value: "CHALLENGE" },
  { label: "건강 데이터", value: "HEALTH_DATA" },
  { label: "리워드", value: "REWARD" },
];

const STATUS_LABEL: Record<InquiryStatus, string> = {
  PENDING: "답변 대기",
  ANSWERED: "답변 완료",
};

const STATUS_STYLE: Record<InquiryStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-700",
  ANSWERED: "bg-green-100 text-green-700",
};

const SHORTCUTS = [
  {
    icon: "💬",
    label: "1:1 문의",
    desc: "궁금한 점을 남겨주세요",
    href: "/support/inquiry",
  },
  {
    icon: "❓",
    label: "자주 묻는 질문",
    desc: "빠른 답변을 찾아보세요",
    href: "#faq",
  },
  {
    icon: "📄",
    label: "이용약관",
    desc: "약관 및 정책 확인",
    href: "/support/terms/service",
  },
  {
    icon: "🚨",
    label: "불편사항 신고",
    desc: "서비스 문제를 알려주세요",
    href: "/support/inquiry/new?category=ERROR_REPORT",
  },
] as const;

const TERMS_LINKS = [
  { label: "이용약관", href: "/support/terms/service" },
  { label: "개인정보 처리방침", href: "/support/terms/privacy" },
  { label: "위치기반 서비스 이용약관", href: "/support/terms/location" },
  { label: "오픈소스 라이선스", href: "/support/terms/opensource" },
] as const;

// ── 컴포넌트 ──────────────────────────────────────────────────────────────────

export default function SupportPage() {
  const [search, setSearch] = useState("");
  const [faqCategory, setFaqCategory] = useState<FAQCategory | "ALL">("ALL");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const {
    data: faqs = [],
    isLoading: faqsLoading,
    isError: faqsError,
  } = useQuery({
    queryKey: ["faqs", faqCategory],
    queryFn: () =>
      getFAQs(faqCategory !== "ALL" ? { category: faqCategory } : undefined),
  });

  const {
    data: inquiries = [],
    isLoading: inquiriesLoading,
    isError: inquiriesError,
  } = useQuery({
    queryKey: ["inquiries", "recent"],
    queryFn: () => listInquiries({ limit: 3 }),
  });

  const filteredFaqs = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return faqs;
    return faqs.filter(
      (f) =>
        f.question.toLowerCase().includes(term) ||
        f.answer.toLowerCase().includes(term),
    );
  }, [faqs, search]);

  return (
    <div className="space-y-8">
      {/* 헤더 + 검색바 */}
      <div>
        <h1 className="text-2xl font-black text-text-primary mb-4">고객센터</h1>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="궁금한 내용을 검색하세요"
          className="w-full px-4 py-3 border border-border rounded-[12px] text-sm outline-none focus:border-brand-black transition-colors bg-white"
        />
      </div>

      {/* 바로가기 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {SHORTCUTS.map(({ icon, label, desc, href }) => (
          <Link
            key={label}
            href={href}
            className="flex flex-col gap-1 p-4 bg-surface rounded-[12px] hover:brightness-95 transition-all"
          >
            <span className="text-2xl">{icon}</span>
            <span className="text-sm font-semibold text-text-primary">{label}</span>
            <span className="text-xs text-text-tertiary">{desc}</span>
          </Link>
        ))}
      </div>

      {/* FAQ 섹션 */}
      <section id="faq">
        <h2 className="text-lg font-bold text-text-primary mb-3">자주 묻는 질문</h2>

        {/* 카테고리 탭 */}
        <div className="flex gap-2 flex-wrap mb-4">
          {FAQ_CATEGORIES.map(({ label, value }) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setFaqCategory(value);
                setExpandedId(null);
              }}
              className={[
                "px-3 py-1.5 rounded-full text-sm transition-colors",
                faqCategory === value
                  ? "bg-brand-black text-white font-semibold"
                  : "bg-surface text-text-secondary hover:text-text-primary",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 아코디언 */}
        {faqsLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-12 bg-surface animate-pulse rounded-[12px]" />
            ))}
          </div>
        ) : faqsError ? (
          <p className="py-10 text-center text-sm text-text-tertiary">FAQ를 불러오지 못했어요. 잠시 후 다시 시도해주세요.</p>
        ) : filteredFaqs.length === 0 ? (
          <p className="py-10 text-center text-sm text-text-tertiary">
            {search ? "검색 결과가 없어요." : "아직 등록된 FAQ가 없어요."}
          </p>
        ) : (
          <div className="divide-y divide-border border border-border rounded-[12px] overflow-hidden">
            {filteredFaqs.map((faq) => (
              <div key={faq.id}>
                <button
                  type="button"
                  onClick={() =>
                    setExpandedId(expandedId === faq.id ? null : faq.id)
                  }
                  className="w-full flex items-center justify-between px-4 py-3.5 text-left hover:bg-surface transition-colors"
                >
                  <span className="text-sm font-medium text-text-primary">
                    {faq.question}
                  </span>
                  <span className="text-text-tertiary ml-3 shrink-0 text-xs">
                    {expandedId === faq.id ? "▲" : "▼"}
                  </span>
                </button>
                {expandedId === faq.id && (
                  <div className="px-4 pb-4 pt-1 text-sm text-text-secondary whitespace-pre-wrap bg-surface/50 leading-relaxed">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 내 문의 목록 (최근 3건) */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-text-primary">내 문의</h2>
          <Link
            href="/support/inquiry"
            className="text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            전체 보기 →
          </Link>
        </div>

        {inquiriesLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-12 bg-surface animate-pulse rounded-[12px]" />
            ))}
          </div>
        ) : inquiriesError ? (
          <p className="py-8 text-center text-sm text-text-tertiary border border-border rounded-[12px]">문의 내역을 불러오지 못했어요. 잠시 후 다시 시도해주세요.</p>
        ) : inquiries.length === 0 ? (
          <div className="py-8 text-center border border-border rounded-[12px]">
            <p className="text-sm text-text-tertiary mb-2">아직 문의 내역이 없어요.</p>
            <Link
              href="/support/inquiry/new"
              className="text-sm font-semibold text-brand-black hover:opacity-70 transition-opacity"
            >
              첫 문의 남기기 →
            </Link>
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-border border border-border rounded-[12px] overflow-hidden">
            {inquiries.map((inq) => (
              <Link
                key={inq.id}
                href={`/support/inquiry/${inq.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-surface transition-colors"
              >
                <span className="text-sm text-text-primary truncate">
                  {inq.title}
                </span>
                <span
                  className={[
                    "ml-3 px-2 py-0.5 rounded-full text-xs font-medium shrink-0",
                    STATUS_STYLE[inq.status],
                  ].join(" ")}
                >
                  {STATUS_LABEL[inq.status]}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* 약관 링크 */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 pt-4 border-t border-border">
        {TERMS_LINKS.map(({ label, href }) => (
          <Link
            key={href}
            href={href}
            className="text-xs text-text-tertiary hover:text-text-secondary transition-colors"
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  );
}
