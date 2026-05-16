"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { SMS_TIMEOUT_SEC, ROUTES } from "@/constants";

/* =========================================
   SMS 인증 페이지
   와이어프레임: mobile 09-A04 (모바일 전용 흐름)
   ========================================= */

export default function SmsVerifyPage() {
  const router = useRouter();
  const { showToast } = useToast();

  /* 6자리 각 셀 */
  const [digits, setDigits] = useState<string[]>(Array(6).fill(""));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  /* 카운트다운 타이머 */
  const [timeLeft, setTimeLeft] = useState(SMS_TIMEOUT_SEC);
  const [expired, setExpired] = useState(false);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (timeLeft <= 0) {
      setExpired(true);
      return;
    }
    const timer = setInterval(() => setTimeLeft((t) => t - 1), 1000);
    return () => clearInterval(timer);
  }, [timeLeft]);

  const formattedTime = `${String(Math.floor(timeLeft / 60)).padStart(2, "0")}:${String(timeLeft % 60).padStart(2, "0")}`;

  const handleDigitInput = (index: number, value: string) => {
    /* 붙여넣기 처리 */
    if (value.length > 1) {
      const pasted = value.replace(/\D/g, "").slice(0, 6);
      const newDigits = [...digits];
      for (let i = 0; i < pasted.length; i++) {
        newDigits[index + i] = pasted[i] ?? "";
      }
      setDigits(newDigits);
      const nextIndex = Math.min(index + pasted.length, 5);
      inputRefs.current[nextIndex]?.focus();
      return;
    }

    const digit = value.replace(/\D/g, "");
    const newDigits = [...digits];
    newDigits[index] = digit;
    setDigits(newDigits);

    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleResend = () => {
    // TODO(backend): /api/v1/auth/sms/send 엔드포인트 추가 필요
    showToast("SMS 재전송은 백엔드 추가 예정입니다", "info");
    setTimeLeft(SMS_TIMEOUT_SEC);
    setExpired(false);
    setDigits(Array(6).fill(""));
    inputRefs.current[0]?.focus();
  };

  const handleVerify = async () => {
    const code = digits.join("");
    if (code.length < 6) {
      showToast("6자리 인증코드를 모두 입력해 주세요", "warning");
      return;
    }
    setVerifying(true);
    try {
      // TODO(backend): /api/v1/auth/sms/verify 엔드포인트 추가 필요
      // await verifySms(phone, code);
      showToast("SMS 인증은 백엔드 추가 예정입니다", "info");
      router.push(ROUTES.LOGIN);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <SimpleAuthShell title="SMS 인증" backHref={ROUTES.LOGIN}>
      <div className="pt-4">
        <h2 className="text-xl font-bold text-text-primary mb-1">
          휴대폰으로 발송된
        </h2>
        <h2 className="text-xl font-bold text-text-primary mb-6">
          6자리 코드를 입력해주세요
        </h2>

        {/* 6자리 입력 박스 */}
        <div
          className="flex gap-2.5 justify-center mb-4"
          role="group"
          aria-label="인증 코드 입력"
        >
          {digits.map((digit, i) => (
            <input
              key={i}
              ref={(el) => {
                inputRefs.current[i] = el;
              }}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={digit}
              onChange={(e) => handleDigitInput(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              aria-label={`인증코드 ${i + 1}번째 자리`}
              className={[
                "w-12 h-14 text-center text-2xl font-bold",
                "border-2 rounded-[8px] transition-colors duration-150",
                "focus:outline-none focus:border-brand-black",
                expired
                  ? "border-status-danger text-status-danger"
                  : digit
                  ? "border-brand-black"
                  : "border-border",
              ].join(" ")}
            />
          ))}
        </div>

        {/* 타이머 + 재전송 */}
        <div className="flex items-center justify-between mb-8 px-1">
          <span
            className={[
              "text-sm font-mono font-medium",
              expired ? "text-status-danger" : "text-text-secondary",
            ].join(" ")}
            aria-live="polite"
            aria-label={`남은 시간 ${formattedTime}`}
          >
            {expired ? "인증 시간이 만료되었습니다" : formattedTime}
          </span>
          <button
            type="button"
            onClick={handleResend}
            className="text-sm text-text-secondary underline underline-offset-2 hover:text-text-primary transition-colors"
          >
            재전송
          </button>
        </div>

        <Button
          variant="secondary"
          size="lg"
          fullWidth
          loading={verifying}
          disabled={digits.join("").length < 6 || expired}
          onClick={handleVerify}
        >
          인증 완료
        </Button>
      </div>
    </SimpleAuthShell>
  );
}
