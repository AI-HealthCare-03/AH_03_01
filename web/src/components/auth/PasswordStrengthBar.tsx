import type { PasswordStrength } from "@/types";

/* =========================================
   비밀번호 강도 표시 바
   ========================================= */

interface PasswordStrengthBarProps {
  strength: PasswordStrength | null;
}

const config: Record<
  PasswordStrength,
  { label: string; color: string; width: string; segments: number }
> = {
  weak: { label: "약함", color: "bg-status-danger", width: "w-1/3", segments: 1 },
  fair: { label: "보통", color: "bg-brand", width: "w-2/3", segments: 2 },
  strong: { label: "강함", color: "bg-status-success", width: "w-full", segments: 3 },
};

export default function PasswordStrengthBar({
  strength,
}: PasswordStrengthBarProps) {
  if (!strength) return null;

  const { label, color, segments } = config[strength];

  return (
    <div className="space-y-1.5">
      {/* 3단계 세그먼트 바 */}
      <div className="flex gap-1.5" aria-hidden="true">
        {[1, 2, 3].map((seg) => (
          <div
            key={seg}
            className={[
              "h-1.5 flex-1 rounded-full transition-colors duration-300",
              seg <= segments ? color : "bg-border",
            ].join(" ")}
          />
        ))}
      </div>
      <p className="text-xs text-text-secondary">
        비밀번호 강도:{" "}
        <span
          className={
            strength === "strong"
              ? "text-status-success font-medium"
              : strength === "fair"
              ? "text-[#7a6a00] font-medium"
              : "text-status-danger font-medium"
          }
        >
          {label}
        </span>
      </p>
    </div>
  );
}
