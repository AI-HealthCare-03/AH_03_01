"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import type { Challenge } from "@/types/challenge";

/* =========================================
   설문형 인증 컴포넌트
   질환 관리 - 당뇨발 일일 점검 (9문항)
   method=CHECK + answers 에 9문항 응답 저장
   ========================================= */

interface QuestionnaireVerifyProps {
  challenge: Challenge;
  template: string; /* "DIABETIC_FOOT_DAILY" 등 */
  onSubmit: (answers: Record<string, string>) => void;
  loading?: boolean;
}

interface Question {
  id: string;
  text: string;
  positive: string; /* 정답(건강한 답변) 값 */
  options: { value: string; label: string }[];
}

/* 당뇨발 일일 점검 9문항 (사용자 사양 그대로) */
const DIABETIC_FOOT_QUESTIONS: Question[] = [
  {
    id: "wound",
    text: "오늘 발바닥, 발가락 사이, 뒤꿈치, 발톱 주변에 상처가 있는지 확인하셨나요?",
    positive: "NO",
    options: [
      { value: "YES", label: "있음" },
      { value: "NO", label: "없음" },
    ],
  },
  {
    id: "blister",
    text: "오늘 발바닥, 발가락 사이, 뒤꿈치, 발톱 주변에 물집이 있는지 확인하셨나요?",
    positive: "NO",
    options: [
      { value: "YES", label: "있음" },
      { value: "NO", label: "없음" },
    ],
  },
  {
    id: "redness",
    text: "오늘 발바닥, 발가락 사이, 뒤꿈치, 발톱 주변에 붉은기가 있는지 확인하셨나요?",
    positive: "NO",
    options: [
      { value: "YES", label: "있음" },
      { value: "NO", label: "없음" },
    ],
  },
  {
    id: "crack",
    text: "오늘 발바닥, 발가락 사이, 뒤꿈치, 발톱 주변에 갈라진 곳이 있는지 확인하셨나요?",
    positive: "NO",
    options: [
      { value: "YES", label: "있음" },
      { value: "NO", label: "없음" },
    ],
  },
  {
    id: "discoloration",
    text: "오늘 발바닥, 발가락 사이, 뒤꿈치, 발톱 주변에 색 변화가 있는지 확인하셨나요?",
    positive: "NO",
    options: [
      { value: "YES", label: "있음" },
      { value: "NO", label: "없음" },
    ],
  },
  {
    id: "swelling",
    text: "오늘 발, 다리에 붓기가 느껴지시나요?",
    positive: "NO",
    options: [
      { value: "YES", label: "있음" },
      { value: "NO", label: "없음" },
    ],
  },
  {
    id: "socks_indoor",
    text: "오늘 실내에서도 양말 또는 실내화 착용을 하셨나요?",
    positive: "YES",
    options: [
      { value: "YES", label: "했음" },
      { value: "NO", label: "안했음" },
    ],
  },
  {
    id: "wash_dry",
    text: "오늘 발을 씻고 드라이기로 말려주셨나요?",
    positive: "YES",
    options: [
      { value: "YES", label: "했음" },
      { value: "NO", label: "안했음" },
    ],
  },
  {
    id: "moisturizer",
    text: "오늘 발을 씻고 발가락 사이를 제외한 나머지 부위에 보습제를 발라주셨나요?",
    positive: "YES",
    options: [
      { value: "YES", label: "했음" },
      { value: "NO", label: "안했음" },
    ],
  },
];

const TEMPLATES: Record<string, { title: string; subtitle: string; questions: Question[] }> = {
  DIABETIC_FOOT_DAILY: {
    title: "당뇨발 일일 점검",
    subtitle: "9가지 항목을 솔직하게 답변해 주세요",
    questions: DIABETIC_FOOT_QUESTIONS,
  },
};

export default function QuestionnaireVerify({
  challenge,
  template,
  onSubmit,
  loading = false,
}: QuestionnaireVerifyProps) {
  const tpl = TEMPLATES[template];
  const [answers, setAnswers] = useState<Record<string, string>>({});

  if (!tpl) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-text-tertiary">
          지원하지 않는 설문 템플릿입니다: {template}
        </p>
      </div>
    );
  }

  const allAnswered = tpl.questions.every((q) => answers[q.id]);

  const handleSubmit = () => {
    if (!allAnswered) return;
    onSubmit({
      template,
      ...answers,
    });
  };

  /* 진행률 */
  const answered = Object.keys(answers).length;
  const progress = Math.round((answered / tpl.questions.length) * 100);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="text-center">
        <span className="text-5xl" aria-hidden="true">
          🦶
        </span>
        <h2 className="text-lg font-black text-text-primary mt-3 mb-1">
          {tpl.title}
        </h2>
        <p className="text-sm text-text-secondary">{tpl.subtitle}</p>
        <p className="text-xs text-text-tertiary mt-2">{challenge.title}</p>
      </div>

      {/* 진행률 바 */}
      <div>
        <div className="flex justify-between items-center text-xs text-text-tertiary mb-1">
          <span>
            {answered}/{tpl.questions.length} 답변 완료
          </span>
          <span className="font-semibold">{progress}%</span>
        </div>
        <div className="h-2 bg-surface rounded-full overflow-hidden">
          <div
            className="h-full bg-brand transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 9문항 */}
      <ol className="space-y-4 list-none">
        {tpl.questions.map((q, idx) => {
          const selected = answers[q.id];
          return (
            <li
              key={q.id}
              className="rounded-[14px] border border-border bg-white p-4 space-y-3"
            >
              <p className="text-sm font-semibold text-text-primary leading-relaxed">
                <span className="text-text-tertiary mr-1">{idx + 1}.</span>
                {q.text}
              </p>
              <div className="flex gap-2">
                {q.options.map((opt) => {
                  const isSelected = selected === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() =>
                        setAnswers((prev) => ({ ...prev, [q.id]: opt.value }))
                      }
                      className={[
                        "flex-1 py-2.5 rounded-[10px] border text-sm font-semibold transition-colors",
                        isSelected
                          ? "border-brand-black bg-brand-black text-white"
                          : "border-border bg-white text-text-secondary hover:border-text-secondary",
                      ].join(" ")}
                      aria-pressed={isSelected}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </li>
          );
        })}
      </ol>

      {/* 안내 */}
      <div className="bg-status-info-bg rounded-[12px] px-4 py-3">
        <p className="text-xs text-status-info leading-relaxed">
          모든 항목을 답변하면 인증이 완료됩니다. 응답은 챌린지 기록으로 안전하게
          저장돼요.
        </p>
      </div>

      {/* 제출 */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        disabled={!allAnswered}
        loading={loading}
        onClick={handleSubmit}
      >
        {allAnswered ? "인증 완료" : `${tpl.questions.length - answered}개 답변 남았어요`}
      </Button>
    </div>
  );
}
