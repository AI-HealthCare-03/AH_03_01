"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import SplitAuthShell from "@/components/layout/SplitAuthShell";
import Input, { PasswordInput } from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import { useToast } from "@/components/ui/Toast";
import { loginSchema, type LoginFormValues } from "@/lib/validators";
import { login } from "@/lib/api/auth";
import { useAuthStore } from "@/stores/auth";
import { extractErrorMessage } from "@/lib/api/client";
import { ROUTES } from "@/constants";

/* =========================================
   로그인 페이지
   와이어프레임: mobile 09-A03 / desktop 14-A01
   ========================================= */

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const { showToast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  const onSubmit = async (data: LoginFormValues) => {
    try {
      const res = await login({ email: data.email, password: data.password });
      setAuth(res.access_token);
      router.push(ROUTES.HOME);
    } catch (err) {
      const msg = extractErrorMessage(err);
      showToast(msg, "error");
    }
  };

  const handleKakaoLogin = () => {
    // TODO(backend): 카카오 OAuth /api/v1/auth/kakao 엔드포인트 추가 필요
    showToast("카카오 로그인은 준비 중입니다", "info");
  };

  return (
    <SplitAuthShell brandSubtext="혈압·혈당·생활습관 챌린지로 나만의 건강 루틴을 만들어 보세요. 지금 바로 시작하세요.">
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-8">로그인</h2>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <Input
            label="이메일"
            type="email"
            placeholder="user@example.com"
            autoComplete="email"
            required
            error={errors.email?.message}
            {...register("email")}
          />

          <PasswordInput
            label="비밀번호"
            placeholder="••••••••"
            autoComplete="current-password"
            required
            error={errors.password?.message}
            {...register("password")}
          />

          {/* 100일 유지 + 링크 */}
          <div className="flex items-center justify-between pt-1">
            <Checkbox
              label="100일 유지하기"
              {...register("rememberMe")}
            />
            <div className="flex items-center gap-3 text-sm">
              <Link
                href={ROUTES.FORGOT_ID}
                className="text-text-secondary hover:text-text-primary transition-colors"
              >
                아이디 찾기
              </Link>
              <span className="text-border" aria-hidden="true">|</span>
              <Link
                href={ROUTES.FORGOT_PASSWORD}
                className="text-text-secondary hover:text-text-primary transition-colors"
              >
                비밀번호 찾기
              </Link>
            </div>
          </div>

          <Button
            type="submit"
            variant="secondary"
            size="lg"
            fullWidth
            loading={isSubmitting}
          >
            로그인
          </Button>
        </form>

        {/* 구분선 */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center">
            <span className="px-3 bg-white text-xs text-text-tertiary">또는</span>
          </div>
        </div>

        {/* 카카오 로그인 */}
        <Button
          variant="kakao"
          size="lg"
          fullWidth
          onClick={handleKakaoLogin}
          leftIcon={
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M10 2C5.582 2 2 4.923 2 8.5c0 2.228 1.336 4.19 3.37 5.365L4.5 18l4.09-2.728C8.854 15.423 9.42 15.5 10 15.5c4.418 0 8-2.923 8-6.5S14.418 2 10 2z"
                fill="#191919"
              />
            </svg>
          }
        >
          카카오로 계속하기
        </Button>

        {/* 회원가입 유도 */}
        <p className="mt-6 text-center text-sm text-text-secondary">
          아직 계정이 없으신가요?{" "}
          <Link
            href={ROUTES.SIGNUP}
            className="font-semibold text-text-primary underline underline-offset-2 hover:text-brand-black"
          >
            회원가입
          </Link>
        </p>
      </div>
    </SplitAuthShell>
  );
}
