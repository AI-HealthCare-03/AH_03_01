import type { HealthStatus } from "@/lib/health/status";
import { statusColorClass } from "@/lib/health/status";

interface StatusBadgeProps {
  status: HealthStatus | "N/A";
  size?: "sm" | "md";
}

const naStyle = {
  bg: "bg-surface",
  text: "text-text-tertiary",
  border: "border-border",
};

export default function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const style = status === "N/A" ? naStyle : statusColorClass[status];
  const sizeClass = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  const icon =
    status === "정상" ? "✅" : status === "주의" ? "⚠️" : status === "위험" ? "🚨" : "—";

  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full font-medium border",
        sizeClass,
        style.bg,
        style.text,
        style.border,
      ].join(" ")}
    >
      <span aria-hidden="true">{icon}</span>
      {status}
    </span>
  );
}
