"use client";

import { forwardRef, useState, type InputHTMLAttributes, type ReactNode } from "react";

/* =========================================
   Input 공통 컴포넌트
   ========================================= */

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "prefix"> {
  label?: string;
  error?: string;
  hint?: string;
  suffix?: ReactNode;
  prefix?: ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, suffix, prefix, id, className = "", ...props },
  ref
) {
  const inputId = id ?? (label ? label.replace(/\s/g, "-").toLowerCase() : undefined);
  const hasError = !!error;

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-text-primary">
          {label}
          {props.required && (
            <span className="ml-0.5 text-status-danger" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      <div className="relative flex items-center">
        {prefix && (
          <span className="absolute left-3 text-text-tertiary pointer-events-none">
            {prefix}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={hasError}
          aria-describedby={
            hasError ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
          }
          className={[
            "w-full h-12 px-4 text-base text-text-primary bg-white",
            "border rounded-[8px] transition-colors duration-150",
            "placeholder:text-text-disabled",
            "focus:outline-none focus:border-brand-black",
            hasError
              ? "border-status-danger focus:border-status-danger"
              : "border-border",
            prefix ? "pl-10" : "",
            suffix ? "pr-12" : "",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
          {...props}
        />
        {suffix && (
          <span className="absolute right-3 flex items-center">{suffix}</span>
        )}
      </div>
      {hasError && (
        <p id={`${inputId}-error`} role="alert" className="text-xs text-status-danger">
          {error}
        </p>
      )}
      {!hasError && hint && (
        <p id={`${inputId}-hint`} className="text-xs text-text-tertiary">
          {hint}
        </p>
      )}
    </div>
  );
});

export default Input;

/* PasswordInput — 보이기/숨기기 토글 */
export function PasswordInput(props: InputProps) {
  const [visible, setVisible] = useState(false);
  return (
    <Input
      {...props}
      type={visible ? "text" : "password"}
      suffix={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "비밀번호 숨기기" : "비밀번호 보기"}
          className="text-text-tertiary hover:text-text-primary transition-colors"
        >
          {visible ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      }
    />
  );
}
