"use client";

/* =========================================
   Step3 — WATER / MEDITATION / NO_SMOKING / NO_ALCOHOL
   개인: 매일(DAILY) vs 주간횟수(WEEKLY_COUNT) 선택
   그룹: 자동으로 GROUP_SUM / GROUP_MEMBERS 로 넘어감
   ========================================= */

interface DailyOrWeeklyStepProps {
  categoryLabel: string;
  value: "DAILY" | "WEEKLY_COUNT" | null;
  onChange: (v: "DAILY" | "WEEKLY_COUNT") => void;
}

export default function DailyOrWeeklyStep({
  categoryLabel,
  value,
  onChange,
}: DailyOrWeeklyStepProps) {
  return (
    <div>
      <h2 className="text-lg font-bold text-text-primary mb-1">
        {categoryLabel} 방식
      </h2>
      <p className="text-sm text-text-secondary mb-6">
        매일 달성할지, 주 몇 회 달성할지 선택해 주세요.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button
          type="button"
          onClick={() => onChange("DAILY")}
          className={[
            "flex flex-col items-center gap-3 p-6 rounded-[16px] border-2 transition-all",
            "hover:shadow-md",
            value === "DAILY"
              ? "border-brand-black bg-white shadow-md"
              : "border-border bg-white hover:border-brand",
          ].join(" ")}
          aria-pressed={value === "DAILY"}
        >
          <span className="text-4xl" aria-hidden="true">
            📅
          </span>
          <div className="text-center">
            <p className="font-bold text-text-primary">매일 달성</p>
            <p className="text-xs text-text-secondary mt-1">
              7일 / 14일 / 한 달 기간 선택 가능
            </p>
          </div>
        </button>

        <button
          type="button"
          onClick={() => onChange("WEEKLY_COUNT")}
          className={[
            "flex flex-col items-center gap-3 p-6 rounded-[16px] border-2 transition-all",
            "hover:shadow-md",
            value === "WEEKLY_COUNT"
              ? "border-brand-black bg-white shadow-md"
              : "border-border bg-white hover:border-brand",
          ].join(" ")}
          aria-pressed={value === "WEEKLY_COUNT"}
        >
          <span className="text-4xl" aria-hidden="true">
            📆
          </span>
          <div className="text-center">
            <p className="font-bold text-text-primary">주간 횟수</p>
            <p className="text-xs text-text-secondary mt-1">
              1주일 동안 목표 횟수만 달성하면 성공
            </p>
          </div>
        </button>
      </div>
    </div>
  );
}
