"use client";

import {
  DurationPicker,
  TitleInput,
  RewardPreview,
  Step4Header,
} from "./_shared";
import type { WizardFormState } from "@/types/challenge";

/* =========================================
   DISEASE_CARE 카테고리 Step4 폼
   - DiseaseFootForm  (당뇨발 매일 관리 — 9문항 설문)
   ========================================= */

const DIABETIC_FOOT_QUESTIONS = [
  "오늘 발을 씻고 완전히 건조시켰나요?",
  "발에 상처, 물집, 발적이 있나요?",
  "발톱 상태가 이상하지 않나요?",
  "발바닥에 굳은살이나 티눈이 생기지 않았나요?",
  "발이 차갑거나 저린 느낌이 있나요?",
  "발 냄새가 평소보다 심하지 않나요?",
  "맞는 신발을 착용하고 있나요?",
  "맨발로 다니지 않았나요?",
  "발에 새로운 증상이나 통증이 생겼나요?",
];

export function DiseaseFootForm({
  form,
  onChange,
}: {
  form: WizardFormState;
  onChange: (partial: Partial<WizardFormState>) => void;
}) {
  return (
    <div className="space-y-6">
      <Step4Header />

      {/* 설문 미리보기 */}
      <div>
        <p className="text-sm font-semibold text-text-primary mb-3">
          매일 확인할 9가지 항목
        </p>
        <div className="space-y-2">
          {DIABETIC_FOOT_QUESTIONS.map((q, i) => (
            <div
              key={i}
              className="flex items-start gap-3 p-3 bg-surface rounded-[10px]"
            >
              <span className="w-5 h-5 shrink-0 flex items-center justify-center rounded-full bg-teal-100 text-teal-700 text-xs font-bold">
                {i + 1}
              </span>
              <p className="text-sm text-text-secondary">{q}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="p-3 bg-teal-50 rounded-[10px] border border-teal-200">
        <p className="text-xs text-teal-700 font-medium">
          인증 방식: 9문항 체크리스트 설문 응답 (사진 불필요)
        </p>
        <p className="text-xs text-teal-600 mt-1">
          매일 챌린지 화면에서 9문항에 응답하면 인증 완료됩니다.
        </p>
      </div>

      <DurationPicker
        value={form.duration_days}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <TitleInput value={form.title} onChange={(v) => onChange({ title: v })} />
      <RewardPreview durationDays={form.duration_days} isGroup={false} />
    </div>
  );
}
