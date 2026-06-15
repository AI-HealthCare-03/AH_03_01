"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import type { WizardFormStep7 } from "@/types/health";

interface StepExtrasProps {
  gender: "MALE" | "FEMALE" | undefined;
  defaultValues?: Partial<WizardFormStep7>;
  onSubmit: (data: WizardFormStep7) => void;
  isLoading?: boolean;
}

const CHRONIC_OPTIONS: { value: string; label: string }[] = [
  { value: "NONE", label: "없음" },
  { value: "HYPERTENSION", label: "고혈압" },
  { value: "DIABETES", label: "당뇨병" },
  { value: "HYPERLIPIDEMIA", label: "고지혈증" },
  { value: "HEART_DISEASE", label: "심장 질환" },
  { value: "KIDNEY_DISEASE", label: "신장 질환" },
  { value: "OBESITY", label: "비만" },
];

const PREGNANCY_OPTIONS: { value: "NOT_APPLICABLE" | "PREGNANT" | "POSTPARTUM"; label: string }[] = [
  { value: "NOT_APPLICABLE", label: "해당 없음" },
  { value: "PREGNANT", label: "임신 중" },
  { value: "POSTPARTUM", label: "산후" },
];

/* 만성질환 멀티선택 */
function ChronicDiseaseField({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const toggle = (disease: string) => {
    if (disease === "NONE") {
      onChange(["NONE"]);
      return;
    }
    const without = value.filter((d) => d !== "NONE");
    if (without.includes(disease)) {
      const next = without.filter((d) => d !== disease);
      onChange(next.length === 0 ? ["NONE"] : next);
    } else {
      onChange([...without, disease]);
    }
  };

  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-2">현재 진단받은 만성질환 (복수 선택)</p>
      <div className="flex flex-wrap gap-2">
        {CHRONIC_OPTIONS.map((opt) => {
          const isSelected =
            opt.value === "NONE" ? value.includes("NONE") : value.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={[
                "px-3 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
                isSelected
                  ? "bg-brand-black text-white border-brand-black"
                  : "bg-white text-text-secondary border-border hover:border-text-primary",
              ].join(" ")}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* 3-선택 칩 (예/아니오/모름) */
function TriChoice({
  label,
  hint,
  value,
  onChange,
  options,
}: {
  label: string;
  hint?: string;
  value: number | null;
  onChange: (v: number) => void;
  options: { value: number; label: string }[];
}) {
  return (
    <div>
      <p className="text-sm font-medium text-text-primary mb-0.5">{label}</p>
      {hint && <p className="text-xs text-text-tertiary mb-2">{hint}</p>}
      <div className="flex gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
              value === opt.value
                ? "bg-brand-black text-white border-brand-black"
                : "bg-white text-text-secondary border-border hover:border-text-primary",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function StepExtras({ gender, defaultValues, onSubmit, isLoading }: StepExtrasProps) {
  const isFemale = gender === "FEMALE";

  /* 여성 전용 */
  const [menopause, setMenopause] = useState<number | null>(defaultValues?.is_menopause ?? null);
  const [ocpTaking, setOcpTaking] = useState<boolean | null>(defaultValues?.ocp_taking ?? null);
  const [ocpMonths, setOcpMonths] = useState(defaultValues?.ocp_total_months ?? "");

  /* 빈혈: 예=1 / 아니오=0 / -1=모름 / null=미선택 */
  const [anemia, setAnemia] = useState<number | null>(defaultValues?.anemia ?? null);

  /* 만성질환 */
  const [chronicDiseases, setChronicDiseases] = useState<string[]>(
    defaultValues?.chronic_diseases ?? ["NONE"]
  );

  /* 임신 상태 */
  const [pregnancyStatus, setPregnancyStatus] =
    useState<"NOT_APPLICABLE" | "PREGNANT" | "POSTPARTUM">(
      defaultValues?.pregnancy_status ?? "NOT_APPLICABLE"
    );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      /* 여성=선택값(미응답 null) · 남성=-1 명시 · 성별 미상(me 로딩 전)=null(미전송) */
      is_menopause: gender === "FEMALE" ? menopause : gender === "MALE" ? -1 : null,
      ocp_taking: isFemale ? ocpTaking : null,
      ocp_total_months: isFemale && ocpTaking ? ocpMonths : "",
      /* 1=예 / 0=아니오 / -1=모름 / null=미선택(미전송) */
      anemia: anemia,
      chronic_diseases: chronicDiseases,
      pregnancy_status: pregnancyStatus,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* 여성 전용 섹션 */}
      {isFemale && (
        <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
          <div>
            <h2 className="font-bold text-lg text-text-primary">여성 건강 정보</h2>
            <p className="text-sm text-text-secondary mt-0.5">선택 입력 — 건너뛸 수 있습니다.</p>
          </div>

          <TriChoice
            label="현재 폐경 상태이신가요?"
            hint="자연 또는 인공 폐경 포함"
            value={menopause}
            onChange={setMenopause}
            options={[
              { value: 1, label: "예" },
              { value: 0, label: "아니오" },
            ]}
          />

          <TriChoice
            label="현재 호르몬제(경구피임약 등)를 복용 중이신가요?"
            value={ocpTaking === null ? -999 : ocpTaking ? 1 : 0}
            onChange={(v) => setOcpTaking(v === 1)}
            options={[
              { value: 1, label: "예" },
              { value: 0, label: "아니오" },
            ]}
          />

          {ocpTaking === true && (
            <div>
              <label
                htmlFor="ocp_months"
                className="text-sm font-medium text-text-primary mb-1 block"
              >
                복용하신 지 얼마나 되셨나요?
              </label>
              <div className="relative">
                <input
                  id="ocp_months"
                  type="number"
                  inputMode="numeric"
                  placeholder="12"
                  value={ocpMonths}
                  onChange={(e) => setOcpMonths(e.target.value)}
                  className="w-full h-12 px-4 pr-14 border border-border rounded-[12px] text-text-primary bg-white focus:outline-none focus:border-brand-black transition-colors"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary">
                  개월
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 추가 정보 */}
      <div className="bg-white rounded-[16px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.08)] space-y-5">
        <div>
          <h2 className="font-bold text-lg text-text-primary">추가 정보</h2>
          <p className="text-sm text-text-secondary mt-0.5">
            마지막 단계입니다. 저장 후 위험도를 계산합니다.
          </p>
        </div>

        {/* 빈혈 */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-2">현재 빈혈이 있으신가요?</p>
          <div className="flex gap-2">
            {[
              { v: 1, label: "예" },
              { v: 0, label: "아니오" },
              { v: -1, label: "모름" },
            ].map(({ v, label }) => (
              <button
                key={v}
                type="button"
                onClick={() => setAnemia(v)}
                className={[
                  "flex-1 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
                  anemia === v
                    ? "bg-brand-black text-white border-brand-black"
                    : "bg-white text-text-secondary border-border hover:border-text-primary",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <ChronicDiseaseField value={chronicDiseases} onChange={setChronicDiseases} />

        {/* 임신 상태 — 여성만 표시 */}
        {isFemale && (
          <div>
            <p className="text-sm font-medium text-text-primary mb-2">현재 임신 상태</p>
            <div className="flex flex-wrap gap-2">
              {PREGNANCY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setPregnancyStatus(opt.value)}
                  className={[
                    "px-3 py-2 text-sm rounded-[10px] border transition-colors min-h-[44px]",
                    pregnancyStatus === opt.value
                      ? "bg-brand-black text-white border-brand-black"
                      : "bg-white text-text-secondary border-border hover:border-text-primary",
                  ].join(" ")}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <Button type="submit" fullWidth loading={isLoading}>
        저장 완료
      </Button>
    </form>
  );
}
