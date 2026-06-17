"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import { useToast } from "@/components/ui/Toast";
import {
  emailSchema,
  nameSchema,
  nicknameSchema,
  phoneSchema,
  birthDateSchema,
  genderSchema,
  formatPhoneNumber,
} from "@/lib/validators";
import { kakaoSignup } from "@/lib/api/auth";
import { extractErrorMessage } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth";
import {
  ROUTES,
  KAKAO_TICKET_KEY,
  KAKAO_PREFILL_KEY,
} from "@/constants";

/* =========================================
   카카오 소셜 회원가입 — 추가 정보 입력
   경로: /kakao/complete-signup
   콜백에서 signup_ticket / prefill 을 sessionStorage 로 전달받아 진입한다.
   기존 회원가입 폼과 동일한 필드(비밀번호 제외)를 수집한다.
   ========================================= */

const kakaoCompleteSchema = z.object({
  email: emailSchema,
  name: nameSchema,
  nickname: nicknameSchema,
  phone_number: phoneSchema,
  birth_date: birthDateSchema,
  gender: genderSchema,
  agreeTerms: z.literal(true, {
    error: "이용약관에 동의해 주세요",
  }),
  agreePrivacy: z.literal(true, {
    error: "개인정보 처리방침에 동의해 주세요",
  }),
});

type KakaoCompleteFormValues = z.infer<typeof kakaoCompleteSchema>;

export default function KakaoCompleteSignupPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const { setAuth } = useAuthStore();
  const [ticket, setTicket] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<KakaoCompleteFormValues>({
    resolver: zodResolver(kakaoCompleteSchema),
    defaultValues: {
      email: "",
      name: "",
      nickname: "",
      phone_number: "",
      birth_date: "",
      gender: undefined,
    },
  });

  /* 진입 시 ticket / prefill 로드. ticket 이 없으면 정상 진입이 아니므로 로그인으로 돌려보낸다. */
  useEffect(() => {
    const savedTicket = sessionStorage.getItem(KAKAO_TICKET_KEY);
    if (!savedTicket) {
      showToast("카카오 인증 정보가 없습니다. 다시 시도해 주세요.", "info");
      router.replace(ROUTES.LOGIN);
      return;
    }
    setTicket(savedTicket);

    const rawPrefill = sessionStorage.getItem(KAKAO_PREFILL_KEY);
    if (rawPrefill) {
      try {
        const prefill = JSON.parse(rawPrefill) as {
          nickname: string | null;
          email: string | null;
        };
        reset((prev) => ({
          ...prev,
          email: prefill.email ?? "",
          nickname: prefill.nickname ?? "",
        }));
      } catch {
        /* prefill 파싱 실패는 무시하고 빈 폼으로 진행 */
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = async (data: KakaoCompleteFormValues) => {
    if (!ticket) {
      showToast("카카오 인증 정보가 만료되었습니다. 다시 시도해 주세요.", "error");
      router.replace(ROUTES.LOGIN);
      return;
    }
    try {
      const res = await kakaoSignup({
        signup_ticket: ticket,
        email: data.email,
        name: data.name,
        nickname: data.nickname,
        gender: data.gender,
        birth_date: data.birth_date,
        phone_number: data.phone_number.replace(/-/g, ""),
        terms_agreed: data.agreeTerms,
        privacy_agreed: data.agreePrivacy,
      });
      sessionStorage.removeItem(KAKAO_TICKET_KEY);
      sessionStorage.removeItem(KAKAO_PREFILL_KEY);
      setAuth(res.access_token);
      showToast("가입이 완료되었습니다.", "success");
      router.replace(ROUTES.HOME);
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 401) {
        /* signup_ticket 만료/무효 — 처음부터 다시 */
        sessionStorage.removeItem(KAKAO_TICKET_KEY);
        sessionStorage.removeItem(KAKAO_PREFILL_KEY);
        showToast("카카오 인증 세션이 만료되었습니다. 다시 시도해 주세요.", "error");
        router.replace(ROUTES.LOGIN);
        return;
      }
      showToast(extractErrorMessage(err), "error");
    }
  };

  return (
    <SimpleAuthShell title="추가 정보 입력" backHref={ROUTES.LOGIN}>
      <p className="pt-2 pb-6 text-sm text-text-secondary">
        카카오 계정으로 가입을 완료하려면 아래 정보를 입력해 주세요.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* 이메일 */}
        <Input
          label="이메일"
          type="email"
          placeholder="example@email.com"
          autoComplete="email"
          required
          error={errors.email?.message}
          {...register("email")}
        />

        {/* 이름 */}
        <Input
          label="이름"
          placeholder="홍길동"
          autoComplete="name"
          required
          error={errors.name?.message}
          {...register("name")}
        />

        {/* 닉네임 */}
        <Input
          label="닉네임"
          placeholder="2~10자"
          required
          error={errors.nickname?.message}
          {...register("nickname")}
        />

        {/* 휴대폰 번호 */}
        <Input
          label="휴대폰 번호"
          type="tel"
          placeholder="010-0000-0000"
          autoComplete="tel"
          required
          error={errors.phone_number?.message}
          {...register("phone_number", {
            onChange: (e) => {
              const formatted = formatPhoneNumber(e.target.value);
              setValue("phone_number", formatted, { shouldValidate: false });
            },
          })}
        />

        {/* 생년월일 */}
        <Input
          label="생년월일"
          type="date"
          placeholder="YYYY-MM-DD"
          required
          error={errors.birth_date?.message}
          {...register("birth_date")}
        />

        {/* 성별 */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-1.5">
            성별 <span className="text-status-danger" aria-hidden="true">*</span>
          </p>
          <Controller
            control={control}
            name="gender"
            render={({ field }) => (
              <div className="flex gap-3">
                {(
                  [
                    { value: "MALE", label: "남" },
                    { value: "FEMALE", label: "여" },
                  ] as const
                ).map(({ value, label }) => (
                  <label
                    key={value}
                    className={[
                      "flex-1 h-12 flex items-center justify-center rounded-[8px] border-2 cursor-pointer",
                      "text-sm font-medium transition-colors",
                      field.value === value
                        ? "border-brand-black bg-brand-black text-white"
                        : "border-border text-text-secondary hover:border-text-secondary",
                    ].join(" ")}
                  >
                    <input
                      type="radio"
                      className="sr-only"
                      value={value}
                      checked={field.value === value}
                      onChange={() => field.onChange(value)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            )}
          />
          {errors.gender && (
            <p role="alert" className="mt-1 text-xs text-status-danger">
              {errors.gender.message}
            </p>
          )}
        </div>

        {/* 동의 */}
        <div className="mt-2 space-y-3 p-4 bg-surface rounded-[12px]">
          <Checkbox
            label={
              <span>
                <Link href="/terms" target="_blank" rel="noreferrer" className="underline">이용약관</Link>에 동의합니다 (필수)
              </span>
            }
            required
            error={errors.agreeTerms?.message}
            {...register("agreeTerms")}
          />
          <Checkbox
            label={
              <span>
                <Link href="/privacy" target="_blank" rel="noreferrer" className="underline">개인정보 처리방침</Link>에 동의합니다 (필수)
              </span>
            }
            required
            error={errors.agreePrivacy?.message}
            {...register("agreePrivacy")}
          />
        </div>

        <Button type="submit" size="lg" fullWidth loading={isSubmitting} className="mt-2">
          가입 완료
        </Button>
      </form>
    </SimpleAuthShell>
  );
}
