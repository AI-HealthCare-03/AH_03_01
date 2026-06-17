"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import axios from "axios";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { emailSchema, nameSchema } from "@/lib/validators";
import { checkEmailVerified, sendEmailVerification, unlockAccount } from "@/lib/api/auth";
import { extractErrorMessage } from "@/lib/api/client";
import { ROUTES } from "@/constants";

/* =========================================
   로그인 잠금 해제 화면 (비밀번호 5회 오류)
   이메일(아이디)+이름 → 이메일 본인 인증 → 잠금 해제
   비밀번호 찾기(forgot-password)와 동일한 인증 패턴, 마지막 단계만 "잠금 해제".
   ========================================= */

const TOKEN_TTL_SEC = 10 * 60; // 인증 메일 토큰 유효시간 (백엔드와 일치)
const VERIFIED_TTL_SEC = 15 * 60; // 인증 완료 상태 유효시간
const formatRemaining = (s: number) =>
  `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

const unlockSchema = z.object({ email: emailSchema, name: nameSchema });
type UnlockFormValues = z.infer<typeof unlockSchema>;

/* 단계 인디케이터 */
function StepIndicator({ current }: { current: 1 | 2 | 3 }) {
  const steps = [
    { num: 1, label: "본인 확인" },
    { num: 2, label: "이메일 인증" },
    { num: 3, label: "잠금 해제" },
  ];
  return (
    <div className="flex items-center gap-2 mb-8">
      {steps.map((step, idx) => {
        const done = step.num < current;
        const active = step.num === current;
        return (
          <div key={step.num} className="flex items-center gap-2">
            <div className="flex flex-col items-center gap-1">
              <div
                className={[
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold",
                  done ? "bg-status-success text-white" : active ? "bg-brand-black text-white" : "bg-border text-text-tertiary",
                ].join(" ")}
                aria-current={active ? "step" : undefined}
              >
                {done ? "✓" : step.num}
              </div>
              <span className="text-[10px] text-text-tertiary whitespace-nowrap">{step.label}</span>
            </div>
            {idx < steps.length - 1 && (
              <div className={["h-px w-8 mb-4 transition-colors", done ? "bg-status-success" : "bg-border"].join(" ")} />
            )}
          </div>
        );
      })}
    </div>
  );
}

type VerifyState = "idle" | "sending" | "sent" | "verified";

export default function LoginBlockedPage() {
  const { showToast } = useToast();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [emailVerify, setEmailVerify] = useState<VerifyState>("idle");
  const [verifyDeadline, setVerifyDeadline] = useState<number | null>(null);
  const [remainingSec, setRemainingSec] = useState(0);
  const [verifyChecking, setVerifyChecking] = useState(false);
  const [unlocking, setUnlocking] = useState(false);
  const [done, setDone] = useState(false);

  const {
    register,
    getValues,
    setValue,
    formState: { errors },
  } = useForm<UnlockFormValues>({
    resolver: zodResolver(unlockSchema),
    defaultValues: { email: "", name: "" },
  });

  /* 로그인 화면에서 넘어온 이메일 prefill */
  useEffect(() => {
    const saved = sessionStorage.getItem("lockout_email");
    if (saved) setValue("email", saved);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* 인증 유효시간 카운트다운 */
  useEffect(() => {
    if (verifyDeadline === null) {
      setRemainingSec(0);
      return;
    }
    const tick = () => {
      const rem = Math.max(0, Math.round((verifyDeadline - Date.now()) / 1000));
      setRemainingSec(rem);
      if (rem <= 0) {
        // 토큰/인증 유효시간 만료 → 1단계로 되돌려 인증 메일 보내기 재활성화
        setEmailVerify("idle");
        setVerifyDeadline(null);
        setStep(1);
        showToast("인증 유효 시간이 만료되었어요. 다시 인증해 주세요.", "info");
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verifyDeadline]);

  const handleSendVerification = async () => {
    const email = getValues("email");
    const name = getValues("name");
    if (!email || !name) {
      showToast("이메일과 이름을 먼저 입력해 주세요", "info");
      return;
    }
    setEmailVerify("sending");
    try {
      await sendEmailVerification(email, name);
      setEmailVerify("sent");
      setVerifyDeadline(Date.now() + TOKEN_TTL_SEC * 1000);
      setStep(2);
      showToast("인증 메일을 보냈어요. 메일함에서 링크를 확인해 주세요.", "success");
    } catch (err) {
      setEmailVerify("idle");
      showToast(extractErrorMessage(err), "error");
    }
  };

  const handleCheckVerified = async () => {
    setVerifyChecking(true);
    try {
      const ok = await checkEmailVerified(getValues("email"));
      if (ok) {
        setEmailVerify("verified");
        setVerifyDeadline(Date.now() + VERIFIED_TTL_SEC * 1000);
        setStep(3);
        showToast("이메일 인증이 완료되었어요", "success");
      } else {
        showToast("아직 인증 전이에요. 메일의 링크를 클릭해 주세요.", "info");
      }
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setVerifyChecking(false);
    }
  };

  const handleUnlock = async () => {
    if (emailVerify !== "verified") {
      showToast("이메일 본인 인증을 먼저 완료해 주세요", "info");
      return;
    }
    setUnlocking(true);
    try {
      await unlockAccount(getValues("email"), getValues("name"));
      sessionStorage.removeItem("lockout_email");
      setDone(true);
    } catch (err) {
      const status = axios.isAxiosError(err) ? err.response?.status : undefined;
      if (status === 404) {
        showToast("일치하는 계정을 찾을 수 없습니다. 이메일과 이름을 확인해 주세요.", "error");
      } else if (status === 400) {
        showToast("이메일 본인 인증을 먼저 완료해 주세요", "error");
      } else {
        showToast(extractErrorMessage(err), "error");
      }
    } finally {
      setUnlocking(false);
    }
  };

  /* 완료 화면 */
  if (done) {
    return (
      <SimpleAuthShell title="로그인 잠금 해제" backHref={ROUTES.LOGIN}>
        <div className="pt-8 text-center">
          <div className="text-5xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-text-primary mb-2">잠금이 해제되었습니다</h2>
          <p className="text-sm text-text-secondary mb-8">다시 로그인해 주세요</p>
          <Link href={ROUTES.LOGIN}>
            <Button variant="secondary" size="lg" fullWidth>
              로그인하기
            </Button>
          </Link>
        </div>
      </SimpleAuthShell>
    );
  }

  return (
    <SimpleAuthShell title="로그인 잠금 해제" backHref={ROUTES.LOGIN}>
      <div className="pt-4">
        <p className="text-sm text-text-secondary mb-6 leading-relaxed">
          비밀번호를 5회 이상 틀려 로그인이 제한되었습니다.
          <br />
          가입한 이메일·이름으로 본인 인증 후 잠금을 해제해 주세요.
        </p>

        <StepIndicator current={step} />

        {/* 1·2단계: 이메일 + 이름 + 본인 인증 */}
        {step !== 3 && (
          <div className="space-y-4">
            <Input
              label="이메일(아이디)"
              type="email"
              placeholder="가입한 이메일 주소"
              required
              error={errors.email?.message}
              disabled={emailVerify === "verified"}
              {...register("email")}
            />
            <Input
              label="이름"
              type="text"
              placeholder="가입 시 입력한 이름"
              required
              error={errors.name?.message}
              disabled={emailVerify === "verified"}
              {...register("name")}
            />

            <Button
              type="button"
              variant="secondary"
              size="lg"
              fullWidth
              loading={emailVerify === "sending"}
              onClick={handleSendVerification}
            >
              {emailVerify === "sent" ? "인증 메일 다시 보내기" : "인증 메일 받기"}
            </Button>

            {emailVerify === "sent" && (
              <div className="space-y-2">
                <p className="text-xs text-text-secondary">
                  메일함의 링크를 클릭한 뒤 아래 버튼을 눌러 주세요{" "}
                  {remainingSec > 0 && (
                    <span className="text-status-danger">(유효 시간 {formatRemaining(remainingSec)})</span>
                  )}
                </p>
                <Button type="button" variant="primary" size="md" fullWidth loading={verifyChecking} onClick={handleCheckVerified}>
                  인증 완료 확인
                </Button>
              </div>
            )}
          </div>
        )}

        {/* 3단계: 잠금 해제 */}
        {step === 3 && (
          <div className="space-y-4">
            <p className="text-xs text-status-success">✓ 이메일 인증 완료</p>
            {remainingSec > 0 && (
              <p className="text-xs text-text-secondary">
                인증 유효 시간 {formatRemaining(remainingSec)} — 시간 내 잠금을 해제해 주세요
              </p>
            )}
            <Button type="button" variant="secondary" size="lg" fullWidth loading={unlocking} onClick={handleUnlock}>
              잠금 해제하기
            </Button>
          </div>
        )}

        <p className="mt-8 text-center text-sm text-text-secondary">
          비밀번호가 기억나지 않으시나요?{" "}
          <Link
            href={ROUTES.FORGOT_PASSWORD}
            className="font-semibold text-text-primary underline underline-offset-2 hover:text-brand-black"
          >
            비밀번호 찾기
          </Link>
        </p>
      </div>
    </SimpleAuthShell>
  );
}
