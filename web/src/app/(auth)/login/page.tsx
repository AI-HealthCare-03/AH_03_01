"use client";

import axios from "axios";
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
      // 5회 실패 잠금(423) → 이메일 인증 잠금 해제 화면으로 안내(이메일 prefill).
      if (axios.isAxiosError(err) && err.response?.status === 423) {
        sessionStorage.setItem("lockout_email", data.email);
        router.push(ROUTES.LOGIN_BLOCKED);
        return;
      }
      showToast(extractErrorMessage(err), "error");
    }
  };

  const handleKakaoLogin = () => {
    // TODO(backend): 카카오 OAuth /api/v1/auth/kakao 엔드포인트 추가 필요
    showToast("카카오 로그인은 준비 중입니다", "info");
  };

  const BOTTOM_FEATURES = [
    {
      label: "안전한 보안",
      bg: "bg-blue-50",
      color: "#3B82F6",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
          <path d="M12 2L4 6v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V6L12 2z" stroke="#3B82F6" strokeWidth="1.8" strokeLinejoin="round" fill="#DBEAFE"/>
          <path d="M9 12l2 2 4-4" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
    },
    {
      label: "간편한 기록",
      bg: "bg-amber-50",
      color: "#F59E0B",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
          <rect x="5" y="3" width="14" height="18" rx="2" stroke="#F59E0B" strokeWidth="1.8" fill="#FEF3C7"/>
          <path d="M9 8h6M9 12h6M9 16h4" stroke="#F59E0B" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: "건강에 맞춤",
      bg: "bg-green-50",
      color: "#10B981",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
          <path d="M4 20V14M9 20V8M14 20V12M19 20V4" stroke="#10B981" strokeWidth="2.2" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: "이웃과 공유",
      bg: "bg-purple-50",
      color: "#8B5CF6",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
          <circle cx="9" cy="7" r="3" stroke="#8B5CF6" strokeWidth="1.8" fill="#EDE9FE"/>
          <path d="M3 21v-2a4 4 0 014-4h4a4 4 0 014 4v2" stroke="#8B5CF6" strokeWidth="1.8" strokeLinecap="round"/>
          <path d="M16 3.13a4 4 0 010 7.75" stroke="#8B5CF6" strokeWidth="1.8" strokeLinecap="round"/>
          <path d="M21 21v-2a4 4 0 00-3-3.87" stroke="#8B5CF6" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
  ];

  return (
    <SplitAuthShell>
      {/* 전체 레이아웃: 카드 + 하단 얕은 바 */}
      <div className="flex flex-col min-h-full px-6 md:px-10 py-8 md:py-10 gap-4">

        {/* ── 로그인 카드 ── */}
        <div className="bg-white rounded-3xl border border-gray-200 shadow-sm px-8 py-8">
          {/* 인사 */}
          <h2 className="text-2xl font-bold text-text-primary mb-1">👋 반가워요!</h2>
          <p className="text-sm text-text-secondary mb-8">
            케어로그에 로그인하여 케어로그를 이용해 보세요.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
            <Input
              label="이메일"
              type="email"
              placeholder="이메일 주소를 입력하세요"
              autoComplete="email"
              required
              error={errors.email?.message}
              {...register("email")}
            />

            <PasswordInput
              label="비밀번호"
              placeholder="비밀번호를 입력하세요"
              autoComplete="current-password"
              required
              error={errors.password?.message}
              {...register("password")}
            />

            {/* 로그인 상태 유지 + 링크 */}
            <div className="flex items-center justify-between pt-1">
              <Checkbox
                label="로그인 상태 유지"
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
              <span className="px-3 bg-white text-xs text-text-tertiary font-medium">또는</span>
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

        {/* ── 하단 4가지 기능 얕은 바 ── */}
        <div className="auth-bottom-bar bg-gray-50 border border-gray-100 rounded-2xl px-6 py-5">
          <div className="grid grid-cols-4 gap-3 mb-3">
            {BOTTOM_FEATURES.map(({ icon, label, bg }) => (
              <div key={label} className="flex flex-col items-center gap-2">
                <div className={`w-12 h-12 ${bg} rounded-2xl flex items-center justify-center`}>
                  {icon}
                </div>
                <span className="text-xs font-medium text-text-secondary text-center leading-tight">{label}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-text-tertiary text-center">
            케어로그는 안전한 환경에서 여러분의 건강 습관을 응원합니다.
          </p>
        </div>
      </div>
    </SplitAuthShell>
  );
}
