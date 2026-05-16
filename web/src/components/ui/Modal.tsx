"use client";

import { useEffect, type ReactNode } from "react";

/* =========================================
   Modal 공통 컴포넌트
   ========================================= */

interface ModalProps {
  open: boolean;
  onClose?: () => void;
  title?: string;
  children: ReactNode;
  maxWidth?: "sm" | "md" | "lg";
}

const maxWidthClasses = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
};

export default function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth = "md",
}: ModalProps) {
  /* ESC 키로 닫기 */
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  /* body 스크롤 잠금 */
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      {/* 오버레이 */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 모달 본문 */}
      <div
        className={[
          "relative w-full bg-white rounded-[16px] shadow-[0_20px_60px_rgba(0,0,0,0.2)]",
          "animate-in fade-in zoom-in-95 duration-200",
          maxWidthClasses[maxWidth],
        ].join(" ")}
      >
        {title && (
          <div className="px-6 pt-6 pb-0">
            <h2 id="modal-title" className="text-lg font-bold text-text-primary">
              {title}
            </h2>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
