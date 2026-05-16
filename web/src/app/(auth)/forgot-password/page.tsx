"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useWatch } from "react-hook-form";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Input, { PasswordInput } from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import PasswordStrengthBar from "@/components/auth/PasswordStrengthBar";
import { useToast } from "@/components/ui/Toast";
import {
  forgotPasswordSchema,
  type ForgotPasswordFormValues,
  getPasswordStrength,
  formatPhoneNumber,
} from "@/lib/validators";
import { ROUTES } from "@/constants";

/* =========================================
   비밀번호 재설정 페이지
   와이어프레임: mobile 09-A06
   단계 인디케이터: ✓ 2 3 (SMS 인증 완료 가정 후 새 비밀번호 입력)
   ========================================= */

/* 단계 인디케이터 */
function StepIndicator({ current }: { current: 1 | 2 | 3 }) {
  const steps = [
    { num: 1, label: "본인 확인" },
    { num: 2, label: "코드 인증" },
    { num: 3, label: "비밀번호 변경" },
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
                  done
                    ? "bg-status-success text-white"
                    : active
                    ? "bg-brand-black text-white"
                    : "bg-border text-text-tertiary",
                ].join(" ")}
                aria-current={active ? "step" : undefined}
              >
                {done ? "✓" : step.num}
              </div>
              <span className="text-[10px] text-text-tertiary whitespace-nowrap">
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={[
                  "h-px w-8 mb-4 transition-colors",
                  done ? "bg-status-success" : "bg-border",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function ForgotPasswordPage() {
  const { showToast } = useToast();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
      phone_number: "",
      new_password: "",
      new_password_confirm: "",
    },
  });

  const watchedPassword = useWatch({ control, name: "new_password" });
  const passwordStrength =
    watchedPassword?.length > 0 ? getPasswordStrength(watchedPassword) : null;

  const handleStep1 = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO(backend): /api/v1/auth/reset-password (인증메일/SMS 발송) 추가 필요
    showToast("인증 코드 발송은 백엔드 추가 예정입니다", "info");
    setStep(2);
  };

  const handleStep2 = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO(backend): /api/v1/auth/sms/verify 추가 필요
    showToast("SMS 인증은 백엔드 추가 예정입니다", "info");
    setStep(3);
  };

  const onSubmit = async (data: ForgotPasswordFormValues) => {
    try {
      // TODO(backend): /api/v1/auth/reset-password (비번 변경) 추가 필요
      // 이미 사용 중인 비밀번호 에러 케이스 예시:
      if (data.new_password === "Aaaa1234!") {
        setError("new_password", {
          message: "이미 사용 중인 비밀번호입니다",
        });
        return;
      }
      showToast("비밀번호 변경은 백엔드 추가 예정입니다", "info");
      setDone(true);
    } catch {
      showToast("비밀번호 변경에 실패했습니다. 다시 시도해 주세요.", "error");
    }
  };

  /* 완료 화면 */
  if (done) {
    return (
      <SimpleAuthShell title="비밀번호 재설정" backHref={ROUTES.LOGIN}>
        <div className="pt-8 text-center">
          <div className="text-5xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-text-primary mb-2">
            비밀번호가 변경되었습니다
          </h2>
          <p className="text-sm text-text-secondary mb-8">
            새로운 비밀번호로 로그인해 주세요
          </p>
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
    <SimpleAuthShell title="비밀번호 재설정" backHref={ROUTES.LOGIN}>
      <div className="pt-4">
        <h2 className="text-xl font-bold text-text-primary mb-6">
          새 비밀번호를 입력해주세요
        </h2>

        <StepIndicator current={step} />

        {/* 단계 1: 이메일 + 휴대폰 */}
        {step === 1 && (
          <form onSubmit={handleStep1} noValidate className="space-y-4">
            <Input
              label="이메일"
              type="email"
              placeholder="가입한 이메일 주소"
              required
              error={errors.email?.message}
              {...register("email")}
            />
            <Input
              label="휴대폰 번호"
              type="tel"
              placeholder="010-0000-0000"
              required
              error={errors.phone_number?.message}
              {...register("phone_number", {
                onChange: (e) => {
                  setValue(
                    "phone_number",
                    formatPhoneNumber(e.target.value),
                    { shouldValidate: false }
                  );
                },
              })}
            />
            <Button
              type="submit"
              variant="secondary"
              size="lg"
              fullWidth
              className="mt-2"
            >
              인증 코드 받기
            </Button>
          </form>
        )}

        {/* 단계 2: SMS 코드 입력 (간략화) */}
        {step === 2 && (
          <form onSubmit={handleStep2} noValidate className="space-y-4">
            <p className="text-sm text-text-secondary">
              등록된 휴대폰으로 인증 코드를 전송했습니다
            </p>
            <Input
              label="인증 코드"
              type="text"
              inputMode="numeric"
              placeholder="6자리 코드 입력"
              maxLength={6}
            />
            <Button type="submit" variant="secondary" size="lg" fullWidth>
              코드 확인
            </Button>
          </form>
        )}

        {/* 단계 3: 새 비밀번호 */}
        {step === 3 && (
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
            <div className="space-y-1.5">
              <PasswordInput
                label="새 비밀번호"
                placeholder="영문+숫자 8자 이상"
                autoComplete="new-password"
                required
                error={errors.new_password?.message}
                {...register("new_password")}
              />
              <PasswordStrengthBar strength={passwordStrength} />
            </div>

            <PasswordInput
              label="새 비밀번호 확인"
              placeholder="비밀번호를 다시 입력해 주세요"
              autoComplete="new-password"
              required
              error={errors.new_password_confirm?.message}
              {...register("new_password_confirm")}
            />

            <Button
              type="submit"
              variant="secondary"
              size="lg"
              fullWidth
              loading={isSubmitting}
              className="mt-2"
            >
              비밀번호 변경
            </Button>
          </form>
        )}

        <Link href={ROUTES.LOGIN}>
          <Button variant="ghost" size="md" fullWidth className="mt-3">
            로그인으로 돌아가기
          </Button>
        </Link>
      </div>
    </SimpleAuthShell>
  );
}
