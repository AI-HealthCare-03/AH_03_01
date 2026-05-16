"use client";

import { useState, useRef, useEffect } from "react";

interface WaistPopoverProps {
  /** 모바일에서 바텀시트로 렌더 */
  isMobile?: boolean;
}

const WAIST_GUIDE = {
  male: [
    { label: "정상", range: "80cm 미만", color: "text-status-success" },
    { label: "주의", range: "80~89cm", color: "text-[#856404]" },
    { label: "위험", range: "90cm 이상", color: "text-status-danger" },
  ],
  female: [
    { label: "정상", range: "75cm 미만", color: "text-status-success" },
    { label: "주의", range: "75~84cm", color: "text-[#856404]" },
    { label: "위험", range: "85cm 이상", color: "text-status-danger" },
  ],
} as const;

export default function WaistPopover({ isMobile = false }: WaistPopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="ml-1 w-5 h-5 rounded-full bg-surface border border-border text-text-tertiary text-xs font-bold hover:bg-[#e0e0e0] transition-colors"
        aria-label="허리둘레 판정 기준 보기"
        aria-expanded={open}
      >
        ?
      </button>

      {open && (
        <>
          {/* 모바일: 고정 바텀시트 */}
          {isMobile ? (
            <div className="fixed inset-0 z-50 flex items-end">
              <div
                className="absolute inset-0 bg-black/30"
                onClick={() => setOpen(false)}
                aria-hidden="true"
              />
              <div className="relative w-full bg-white rounded-t-[20px] p-6 pb-8">
                <WaistGuideContent onClose={() => setOpen(false)} />
              </div>
            </div>
          ) : (
            /* 데스크탑: floating 팝오버 */
            <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 z-20 w-60 bg-white rounded-[12px] shadow-[0_4px_16px_rgba(0,0,0,0.16)] border border-border p-4">
              <WaistGuideContent onClose={() => setOpen(false)} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function WaistGuideContent({ onClose }: { onClose: () => void }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-text-primary text-sm">허리둘레 판정 기준</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-text-tertiary hover:text-text-primary text-lg leading-none"
          aria-label="닫기"
        >
          ×
        </button>
      </div>
      <div className="space-y-3">
        {(["male", "female"] as const).map((sex) => (
          <div key={sex}>
            <p className="text-xs font-semibold text-text-secondary mb-1">
              {sex === "male" ? "남성" : "여성"}
            </p>
            <div className="space-y-0.5">
              {WAIST_GUIDE[sex].map((row) => (
                <div key={row.label} className="flex justify-between text-xs">
                  <span className={`font-medium ${row.color}`}>{row.label}</span>
                  <span className="text-text-secondary">{row.range}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[10px] text-text-tertiary">출처: KSSO 2022 비만 진료지침</p>
    </div>
  );
}
