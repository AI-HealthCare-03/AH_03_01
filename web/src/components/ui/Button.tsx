import type { ButtonHTMLAttributes, ReactNode } from "react";

/* =========================================
   Button 공통 컴포넌트
   ========================================= */

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger" | "kakao";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  children: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-brand text-brand-black hover:bg-brand-hover active:scale-[0.98] font-semibold",
  secondary:
    "bg-brand-black text-white hover:bg-[#333] active:scale-[0.98] font-semibold",
  outline:
    "bg-white border border-border text-text-primary hover:bg-surface active:scale-[0.98]",
  ghost:
    "bg-transparent text-text-secondary hover:bg-surface active:scale-[0.98]",
  danger:
    "bg-status-danger text-white hover:bg-red-700 active:scale-[0.98] font-semibold",
  kakao:
    "bg-[#FEE500] text-[#191919] hover:bg-[#e6cf00] active:scale-[0.98] font-semibold",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-9 px-4 text-sm rounded-[8px]",
  md: "h-12 px-5 text-base rounded-[12px]",
  lg: "h-14 px-6 text-base rounded-[12px]",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      type="button"
      disabled={isDisabled}
      aria-busy={loading}
      className={[
        "inline-flex items-center justify-center gap-2 transition-all duration-150 select-none",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100",
        variantClasses[variant],
        sizeClasses[size],
        fullWidth ? "w-full" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {loading ? (
        <span
          className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
          aria-hidden="true"
        />
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  );
}
