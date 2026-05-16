import type { ReactNode } from "react";

/* =========================================
   Badge 공통 컴포넌트
   ========================================= */

type BadgeVariant = "danger" | "warning" | "success" | "info" | "default";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  danger: "bg-[#ffeaea] text-status-danger",
  warning: "bg-[#fffbe6] text-[#7a6a00]",
  success: "bg-[#e8f5e9] text-status-success",
  info: "bg-[#e3f2fd] text-status-info",
  default: "bg-surface text-text-secondary",
};

export default function Badge({
  variant = "default",
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-medium rounded-full",
        variantClasses[variant],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}
