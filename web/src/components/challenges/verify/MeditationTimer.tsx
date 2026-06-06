"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Button from "@/components/ui/Button";
import type { Challenge } from "@/types/challenge";

/* =========================================
   명상 타이머 컴포넌트 (4단계)
   MEDITATION 카테고리 그룹 챌린지 인증용
   goal_config.duration_minutes 기준 카운트다운
   완료 → caption 입력 → onSubmit 호출
   ========================================= */

interface MeditationTimerProps {
  challenge: Challenge;
  onSubmit: (durationSeconds: number, caption?: string) => void;
  onCancel: () => void;
  loading?: boolean;
}

type Phase = "idle" | "running" | "paused" | "done";

const CIRCLE_R = 54;
const CIRCLE_CIRCUMFERENCE = 2 * Math.PI * CIRCLE_R;

export default function MeditationTimer({
  challenge,
  onSubmit,
  onCancel,
  loading = false,
}: MeditationTimerProps) {
  const goalConfig = (challenge.goal_config ?? {}) as Record<string, unknown>;
  const targetSeconds = Math.max(
    60,
    ((goalConfig.duration_minutes as number) ?? 5) * 60
  );

  const [phase, setPhase] = useState<Phase>("idle");
  const [remaining, setRemaining] = useState(targetSeconds);
  const [caption, setCaption] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => () => clearTimer(), [clearTimer]);

  const start = () => {
    setPhase("running");
    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current!);
          intervalRef.current = null;
          setPhase("done");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const pause = () => {
    clearTimer();
    setPhase("paused");
  };

  const handleSubmit = () => {
    onSubmit(targetSeconds, caption.trim() || undefined);
  };

  /* 원형 프로그레스 */
  const progress = 1 - remaining / targetSeconds;
  const dashOffset = CIRCLE_CIRCUMFERENCE * (1 - progress);

  const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
  const ss = String(remaining % 60).padStart(2, "0");

  /* 완료 화면 */
  if (phase === "done") {
    return (
      <div className="flex flex-col items-center text-center gap-6">
        <span className="text-6xl" aria-hidden="true">🧘</span>
        <div>
          <h2 className="text-xl font-black text-text-primary mb-1">
            명상 완료!
          </h2>
          <p className="text-sm text-text-secondary">
            {Math.floor(targetSeconds / 60)}분 명상을 마쳤어요
          </p>
        </div>

        <div className="w-full max-w-xs">
          <label
            htmlFor="meditation-caption"
            className="block text-sm font-semibold text-text-primary mb-2 text-left"
          >
            한 마디 <span className="text-text-tertiary font-normal">(선택)</span>
          </label>
          <textarea
            id="meditation-caption"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            rows={3}
            maxLength={500}
            placeholder="명상 소감을 남겨보세요..."
            className="w-full px-4 py-3 rounded-[12px] border border-border text-sm resize-none focus:outline-none focus:border-brand-black"
          />
          <p className="text-xs text-text-tertiary text-right mt-1">
            {caption.length}/500
          </p>
        </div>

        <Button
          variant="primary"
          size="lg"
          fullWidth
          loading={loading}
          onClick={handleSubmit}
          className="max-w-xs"
        >
          인증 완료
        </Button>
      </div>
    );
  }

  /* 타이머 화면 */
  return (
    <div className="flex flex-col items-center text-center gap-6">
      <div>
        <h2 className="text-xl font-black text-text-primary mb-1">
          명상 타이머
        </h2>
        <p className="text-sm text-text-secondary">
          {Math.floor(targetSeconds / 60)}분 동안 명상하세요
        </p>
      </div>

      {/* 원형 타이머 */}
      <div className="relative w-40 h-40">
        <svg
          className="w-full h-full -rotate-90"
          viewBox="0 0 120 120"
          aria-hidden="true"
        >
          {/* 배경 트랙 */}
          <circle
            cx="60"
            cy="60"
            r={CIRCLE_R}
            fill="none"
            stroke="var(--color-border, #e5e7eb)"
            strokeWidth="8"
          />
          {/* 진행 */}
          <circle
            cx="60"
            cy="60"
            r={CIRCLE_R}
            fill="none"
            stroke="#f5c518"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={CIRCLE_CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            style={{ transition: "stroke-dashoffset 0.8s linear" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-black text-text-primary tabular-nums">
            {mm}:{ss}
          </span>
          <span className="text-xs text-text-tertiary mt-0.5">
            {phase === "idle" ? "대기 중" : phase === "paused" ? "일시정지" : "진행 중"}
          </span>
        </div>
      </div>

      {/* 컨트롤 버튼 */}
      <div className="flex gap-3 w-full max-w-xs">
        {phase === "idle" && (
          <Button variant="primary" size="lg" fullWidth onClick={start}>
            시작
          </Button>
        )}
        {phase === "running" && (
          <Button variant="outline" size="lg" fullWidth onClick={pause}>
            일시정지
          </Button>
        )}
        {phase === "paused" && (
          <>
            <Button variant="primary" size="lg" fullWidth onClick={start}>
              재개
            </Button>
          </>
        )}
      </div>

      {/* 취소 */}
      <button
        type="button"
        onClick={onCancel}
        className="text-sm text-text-tertiary hover:text-text-secondary underline"
      >
        취소
      </button>
    </div>
  );
}
