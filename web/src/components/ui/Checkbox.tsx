import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

/* =========================================
   Checkbox 공통 컴포넌트
   ========================================= */

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: ReactNode;
  error?: string;
}

const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, error, id, className = "", ...props },
  ref
) {
  // SSR/클라이언트 hydration 안정성을 위해 React useId 사용 (Math.random 은 mismatch 유발).
  const reactId = useId();
  const inputId = id ?? `checkbox-${reactId}`;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label
        htmlFor={inputId}
        className="flex items-start gap-2.5 cursor-pointer group"
      >
        <input
          ref={ref}
          id={inputId}
          type="checkbox"
          className="sr-only"
          aria-invalid={!!error}
          {...props}
        />
        {/* 커스텀 체크박스 */}
        <span
          className={[
            "mt-0.5 flex-shrink-0 w-5 h-5 rounded-[4px] border-2 transition-colors duration-150",
            "flex items-center justify-center",
            "group-has-[:checked]:bg-brand-black group-has-[:checked]:border-brand-black",
            "group-has-[:focus-visible]:ring-2 group-has-[:focus-visible]:ring-brand group-has-[:focus-visible]:ring-offset-1",
            error ? "border-status-danger" : "border-border",
          ]
            .filter(Boolean)
            .join(" ")}
          aria-hidden="true"
        >
          <svg
            className="w-3 h-3 text-white opacity-0 group-has-[:checked]:opacity-100 transition-opacity"
            viewBox="0 0 12 12"
            fill="none"
          >
            <path
              d="M2 6l3 3 5-5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="text-sm text-text-primary leading-snug">{label}</span>
      </label>
      {error && (
        <p role="alert" className="text-xs text-status-danger ml-7">
          {error}
        </p>
      )}
    </div>
  );
});

export default Checkbox;
