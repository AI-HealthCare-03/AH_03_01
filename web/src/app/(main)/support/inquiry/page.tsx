"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listInquiries } from "@/lib/api/support";
import { CATEGORY_LABEL, STATUS_LABEL, STATUS_STYLE } from "./_constants";

export default function InquiryListPage() {
  const {
    data: inquiries = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["inquiries"],
    queryFn: () => listInquiries({ limit: 100 }),
    staleTime: 0,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-black text-text-primary">1:1 문의</h1>
        <Link
          href="/support/inquiry/new"
          className="px-4 py-2 bg-brand-black text-white text-sm font-semibold rounded-[10px]"
        >
          문의 작성
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 bg-surface animate-pulse rounded-[12px]" />
          ))}
        </div>
      ) : isError ? (
        <p className="py-10 text-center text-sm text-text-tertiary">
          문의 내역을 불러오지 못했어요. 잠시 후 다시 시도해주세요.
        </p>
      ) : inquiries.length === 0 ? (
        <div className="py-12 text-center border border-border rounded-[12px]">
          <p className="text-sm text-text-tertiary mb-3">아직 문의 내역이 없어요.</p>
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
              className="flex flex-col gap-1 px-4 py-3.5 hover:bg-surface transition-colors"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary truncate">
                  {inq.title}
                </span>
                <span
                  className={[
                    "shrink-0 px-2 py-0.5 rounded-full text-xs font-medium",
                    STATUS_STYLE[inq.status],
                  ].join(" ")}
                >
                  {STATUS_LABEL[inq.status]}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-text-tertiary">
                <span>{CATEGORY_LABEL[inq.category]}</span>
                <span>·</span>
                <span>{new Date(inq.created_at).toLocaleDateString("ko-KR")}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
