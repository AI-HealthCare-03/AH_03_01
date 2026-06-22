"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { forgotIdSchema, type ForgotIdFormValues, formatPhoneNumber } from "@/lib/validators";
import { findId } from "@/lib/api/auth";
import { ROUTES } from "@/constants";

/* =========================================
   아이디 찾기 페이지
   와이어프레임: mobile 09-A05
   ========================================= */

interface FoundResult {
  maskedEmail: string | null;
  socialProvider: string | null;
  createdAt: string;
}

export default function ForgotIdPage() {
  const { showToast } = useToast();
  const [result, setResult] = useState<FoundResult | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ForgotIdFormValues>({
    resolver: zodResolver(forgotIdSchema),
    defaultValues: { name: "", phone_number: "" },
  });

  const onSubmit = async (data: ForgotIdFormValues) => {
    try {
      const res = await findId(data.name, data.phone_number);
      setResult({
        maskedEmail: res.maskedEmail,
        socialProvider: res.socialProvider,
        createdAt: res.createdAt,
      });
    } catch {
      showToast("일치하는 계정을 찾을 수 없습니다", "error");
    }
  };

  /* 결과 화면 */
  if (result) {
    return (
      <SimpleAuthShell title="아이디 찾기" backHref={ROUTES.LOGIN}>
        <div className="pt-4">
          <p className="text-sm text-text-secondary mb-6">
            가입 시 입력한 정보를 확인합니다
          </p>

          {result.socialProvider ? (
            /* 소셜(카카오) 계정 — 이메일/비밀번호 로그인이 없으므로 소셜 로그인 안내 */
            <div className="p-5 bg-surface rounded-[12px] space-y-3 mb-8">
              <p className="text-base font-semibold text-text-primary">
                카카오로 가입한 계정입니다
              </p>
              <p className="text-sm text-text-secondary">
                이 계정은 이메일/비밀번호 없이 카카오로 로그인합니다. 로그인 화면에서 “카카오로 계속하기”를 이용해 주세요.
              </p>
              <div>
                <p className="text-xs text-text-tertiary mb-1">가입일</p>
                <p className="text-sm text-text-secondary">{result.createdAt}</p>
              </div>
            </div>
          ) : (
            <div className="p-5 bg-surface rounded-[12px] space-y-3 mb-8">
              <div>
                <p className="text-xs text-text-tertiary mb-1">이메일</p>
                <p className="text-lg font-semibold text-text-primary">
                  {result.maskedEmail}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-tertiary mb-1">가입일</p>
                <p className="text-sm text-text-secondary">{result.createdAt}</p>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <Button
              variant="secondary"
              size="lg"
              fullWidth
              onClick={() => setResult(null)}
            >
              아이디 확인
            </Button>
            <Link href={ROUTES.FORGOT_PASSWORD}>
              <Button variant="outline" size="lg" fullWidth>
                비밀번호 찾기
              </Button>
            </Link>
            <Link href={ROUTES.LOGIN}>
              <Button variant="ghost" size="md" fullWidth>
                로그인으로 돌아가기
              </Button>
            </Link>
          </div>
        </div>
      </SimpleAuthShell>
    );
  }

  /* 입력 화면 */
  return (
    <SimpleAuthShell title="아이디 찾기" backHref={ROUTES.LOGIN}>
      <div className="pt-4">
        <h2 className="text-xl font-bold text-text-primary mb-2">
          아이디 찾기
        </h2>
        <p className="text-sm text-text-secondary mb-8">
          가입 시 입력한 이름과 휴대폰 번호로 아이디를 찾을 수 있습니다
        </p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <Input
            label="이름"
            placeholder="홍길동"
            required
            error={errors.name?.message}
            {...register("name")}
          />

          <Input
            label="휴대폰 번호"
            type="tel"
            placeholder="010-0000-0000"
            required
            error={errors.phone_number?.message}
            {...register("phone_number", {
              onChange: (e) => {
                setValue("phone_number", formatPhoneNumber(e.target.value), {
                  shouldValidate: false,
                });
              },
            })}
          />

          <Button
            type="submit"
            variant="secondary"
            size="lg"
            fullWidth
            loading={isSubmitting}
            className="mt-2"
          >
            아이디 찾기
          </Button>
        </form>

        <Link href={ROUTES.LOGIN}>
          <Button variant="ghost" size="md" fullWidth className="mt-3">
            로그인으로 돌아가기
          </Button>
        </Link>
      </div>
    </SimpleAuthShell>
  );
}
