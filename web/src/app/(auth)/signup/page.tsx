"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useWatch } from "react-hook-form";
import SplitAuthShell from "@/components/layout/SplitAuthShell";
import Input, { PasswordInput } from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import PasswordStrengthBar from "@/components/auth/PasswordStrengthBar";
import { useToast } from "@/components/ui/Toast";
import {
  signupSchema,
  type SignupFormValues,
  getPasswordStrength,
  formatPhoneNumber,
} from "@/lib/validators";
import {
  checkEmailAvailable,
  checkNicknameAvailable,
  sendEmailVerification,
  checkEmailVerified,
  getPreviousAccount,
  signup,
} from "@/lib/api/auth";
import { extractErrorMessage } from "@/lib/api/client";
import { ROUTES } from "@/constants";
import { LAST_SEEN_KEY } from "@/hooks/useNotificationScheduler";

type DuplStatus = "idle" | "checking" | "available" | "taken";

/* =========================================
   회원가입 페이지
   와이어프레임: mobile 09-A01 / desktop 14-A02
   데스크탑: 2단 그리드 / 모바일: 1단
   ========================================= */

export default function SignupPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const {
    register,
    handleSubmit,
    control,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      email: "",
      nickname: "",
      password: "",
      passwordConfirm: "",
      name: "",
      phone_number: "",
      birth_date: "",
      gender: undefined,
    },
  });

  const watchedPassword = useWatch({ control, name: "password" });
  const watchedPasswordConfirm = useWatch({ control, name: "passwordConfirm" });
  const passwordStrength =
    watchedPassword?.length > 0 ? getPasswordStrength(watchedPassword) : null;
  // 비밀번호 일치 인라인 상태: 둘 다 한 글자 이상 입력됐을 때만 평가.
  const passwordMatch: "match" | "mismatch" | null =
    watchedPassword && watchedPasswordConfirm
      ? watchedPassword === watchedPasswordConfirm
        ? "match"
        : "mismatch"
      : null;

  const [emailDupl, setEmailDupl] = useState<DuplStatus>("idle");
  const [nicknameDupl, setNicknameDupl] = useState<DuplStatus>("idle");

  // 이메일 본인 인증 상태: idle → sending(메일 발송중) → sent(발송됨) → verified(인증완료)
  const [emailVerify, setEmailVerify] =
    useState<"idle" | "sending" | "sent" | "verified">("idle");
  const [verifyChecking, setVerifyChecking] = useState(false);

  // 인증 유효시간 카운트다운. 토큰(sent) 10분 / 인증완료(verified) 15분 — 백엔드 TTL 과 일치.
  const TOKEN_TTL_SEC = 10 * 60;
  const VERIFIED_TTL_SEC = 15 * 60;
  const [verifyDeadline, setVerifyDeadline] = useState<number | null>(null); // epoch ms
  const [remainingSec, setRemainingSec] = useState(0);

  useEffect(() => {
    if (verifyDeadline === null) {
      setRemainingSec(0);
      return;
    }
    const tick = () => {
      const rem = Math.max(0, Math.round((verifyDeadline - Date.now()) / 1000));
      setRemainingSec(rem);
      if (rem <= 0) {
        // 토큰/인증 유효시간 만료 → 처음부터 다시 인증 (본인 인증 버튼 재활성화)
        setEmailVerify("idle");
        setVerifyDeadline(null);
        showToast("인증 유효 시간이 만료되었어요. 다시 인증해 주세요.", "info");
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verifyDeadline]);

  const formatRemaining = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  // 이메일 분리 입력 상태
  const EMAIL_DOMAINS = [
    { label: "선택해 주세요", value: "" },
    { label: "gmail.com", value: "gmail.com" },
    { label: "naver.com", value: "naver.com" },
    { label: "kakao.com", value: "kakao.com" },
    { label: "daum.net", value: "daum.net" },
    { label: "hanmail.net", value: "hanmail.net" },
    { label: "outlook.com", value: "outlook.com" },
    { label: "직접 입력", value: "custom" },
  ] as const;

  const [emailLocal, setEmailLocal] = useState("");
  const [emailDomain, setEmailDomain] = useState("");
  const [isCustomDomain, setIsCustomDomain] = useState(false);

  const syncEmail = (local: string, domain: string) => {
    setValue("email", local && domain ? `${local}@${domain}` : "", {
      shouldValidate: false,
    });
    setEmailDupl("idle");
    setEmailVerify("idle"); // 이메일이 바뀌면 인증 상태 초기화
    setVerifyDeadline(null);
  };

  const handleSendVerification = async () => {
    const email = getValues("email");
    if (!email) {
      showToast("이메일을 먼저 입력해 주세요", "info");
      return;
    }
    setEmailVerify("sending");
    try {
      await sendEmailVerification(email);
      setEmailVerify("sent");
      setVerifyDeadline(Date.now() + TOKEN_TTL_SEC * 1000);
      showToast("인증 메일을 보냈어요. 메일함에서 링크를 확인해 주세요.", "success");
    } catch (err) {
      setEmailVerify("idle");
      showToast(extractErrorMessage(err), "error");
    }
  };

  const handleCheckVerified = async () => {
    const email = getValues("email");
    setVerifyChecking(true);
    try {
      const verified = await checkEmailVerified(email);
      if (verified) {
        setEmailVerify("verified");
        setVerifyDeadline(Date.now() + VERIFIED_TTL_SEC * 1000);
        showToast("이메일 인증이 완료되었어요", "success");
      } else {
        showToast("아직 인증이 완료되지 않았어요. 메일의 링크를 클릭해 주세요.", "info");
      }
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setVerifyChecking(false);
    }
  };

  const onSubmit = async (data: SignupFormValues) => {
    try {
      await signup({
        email: data.email,
        password: data.password,
        name: data.name,
        nickname: data.nickname,
        gender: data.gender,
        birth_date: data.birth_date,
        phone_number: data.phone_number.replace(/-/g, ""),
      });
      localStorage.setItem(LAST_SEEN_KEY, Date.now().toString());
      showToast("가입이 완료되었습니다. 로그인해 주세요.", "success");
      router.push(ROUTES.LOGIN);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    }
  };

  const handleEmailDuplCheck = async () => {
    const email = getValues("email");
    if (!email) {
      showToast("이메일을 먼저 입력해 주세요", "info");
      return;
    }
    setEmailDupl("checking");
    try {
      const res = await checkEmailAvailable(email);
      if (!res.available) {
        // 사용 중인 이메일이 '복구 가능한 탈퇴 계정'이면 복구 안내 페이지로 이동한다.
        const previous = await getPreviousAccount(email);
        if (previous) {
          router.push(`${ROUTES.ACCOUNT_RESTORE}?email=${encodeURIComponent(email)}`);
          return;
        }
        setEmailDupl("taken");
        showToast("이미 사용 중인 이메일입니다", "error");
        return;
      }
      setEmailDupl("available");
      showToast("사용 가능한 이메일이에요", "success");
    } catch (err) {
      setEmailDupl("idle");
      showToast(extractErrorMessage(err), "error");
    }
  };

  const handleNicknameDuplCheck = async () => {
    const nickname = getValues("nickname");
    if (!nickname) {
      showToast("닉네임을 먼저 입력해 주세요", "info");
      return;
    }
    setNicknameDupl("checking");
    try {
      const res = await checkNicknameAvailable(nickname);
      setNicknameDupl(res.available ? "available" : "taken");
      showToast(
        res.available ? "사용 가능한 닉네임이에요" : "이미 사용 중인 닉네임입니다",
        res.available ? "success" : "error",
      );
    } catch (err) {
      setNicknameDupl("idle");
      showToast(extractErrorMessage(err), "error");
    }
  };

  return (
    <SplitAuthShell>
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-2">회원가입</h2>
        <p className="text-sm text-text-secondary mb-8">
          헬씨루틴과 함께 건강한 일상을 시작하세요
        </p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          {/* 2단 그리드 (데스크탑) / 1단 (모바일) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-5 gap-y-4">
            {/* 이메일 */}
            <div className="space-y-1.5 md:col-span-2">
              <p className="text-sm font-medium text-text-primary">
                이메일 <span className="text-status-danger" aria-hidden="true">*</span>
              </p>
              {/* 로컬파트 + @ + 도메인 선택/직접입력 */}
              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  placeholder="example"
                  value={emailLocal}
                  onChange={(e) => {
                    setEmailLocal(e.target.value);
                    syncEmail(e.target.value, emailDomain);
                  }}
                  className="flex-1 h-12 px-3 rounded-[8px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white"
                />
                <span className="text-text-secondary font-medium shrink-0">@</span>
                {isCustomDomain ? (
                  <input
                    type="text"
                    placeholder="직접 입력"
                    value={emailDomain}
                    onChange={(e) => {
                      setEmailDomain(e.target.value);
                      syncEmail(emailLocal, e.target.value);
                    }}
                    className="flex-1 h-12 px-3 rounded-[8px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white"
                  />
                ) : (
                  <select
                    value={emailDomain}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === "custom") {
                        setIsCustomDomain(true);
                        setEmailDomain("");
                        syncEmail(emailLocal, "");
                      } else {
                        setEmailDomain(val);
                        syncEmail(emailLocal, val);
                      }
                    }}
                    className="flex-1 h-12 px-2 rounded-[8px] border border-border text-sm focus:outline-none focus:border-brand-black bg-white"
                  >
                    {EMAIL_DOMAINS.map((d) => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                )}
              </div>
              {/* react-hook-form 연동용 hidden input */}
              <input type="hidden" {...register("email")} />
              {errors.email && (
                <p role="alert" className="text-xs text-status-danger">{errors.email.message}</p>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleEmailDuplCheck}
                loading={emailDupl === "checking"}
                className="w-full"
              >
                중복 확인
              </Button>
              {emailDupl === "available" && (
                <p className="text-xs text-status-success">✓ 사용 가능한 이메일이에요</p>
              )}
              {emailDupl === "taken" && (
                <p className="text-xs text-status-danger">이미 사용 중인 이메일입니다</p>
              )}

              {/* 이메일 본인 인증 */}
              {emailVerify === "verified" ? (
                <>
                  <p className="text-xs text-status-success">✓ 이메일 인증 완료</p>
                  {remainingSec > 0 && (
                    <p className="text-xs text-text-secondary">
                      가입 유효 시간 {formatRemaining(remainingSec)} — 시간 내 가입을 완료해 주세요
                    </p>
                  )}
                </>
              ) : (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSendVerification}
                    loading={emailVerify === "sending"}
                    className="w-full"
                  >
                    {emailVerify === "sent" ? "인증 메일 다시 보내기" : "본인 인증"}
                  </Button>
                  {emailVerify === "sent" && (
                    <>
                      <p className="text-xs text-text-secondary">
                        메일함의 링크를 클릭한 뒤 아래 버튼을 눌러 주세요
                        {remainingSec > 0 && (
                          <>
                            {" "}
                            <span className="text-status-danger">
                              (유효 시간 {formatRemaining(remainingSec)})
                            </span>
                          </>
                        )}
                      </p>
                      <Button
                        type="button"
                        variant="primary"
                        size="sm"
                        onClick={handleCheckVerified}
                        loading={verifyChecking}
                        className="w-full"
                      >
                        인증 완료 확인
                      </Button>
                    </>
                  )}
                </>
              )}
            </div>

            {/* 닉네임 */}
            <div className="space-y-1.5 md:col-span-2">
              <Input
                label="닉네임"
                placeholder="healthy_example"
                required
                error={errors.nickname?.message}
                {...register("nickname", {
                  onChange: () => setNicknameDupl("idle"),
                })}
              />
              <p className="text-xs text-text-secondary">
                영문·숫자·언더바(_)만 사용 가능, 공백 불가
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleNicknameDuplCheck}
                loading={nicknameDupl === "checking"}
                className="w-full"
              >
                중복 확인
              </Button>
              {nicknameDupl === "available" && (
                <p className="text-xs text-status-success">✓ 사용 가능한 닉네임이에요</p>
              )}
              {nicknameDupl === "taken" && (
                <p className="text-xs text-status-danger">이미 사용 중인 닉네임입니다</p>
              )}
            </div>

            {/* 비밀번호 */}
            <div className="space-y-1.5">
              <PasswordInput
                label="비밀번호"
                placeholder="영문+숫자 8자 이상"
                autoComplete="new-password"
                required
                error={errors.password?.message}
                {...register("password")}
              />
              <PasswordStrengthBar strength={passwordStrength} />
            </div>

            {/* 비밀번호 확인 */}
            <div className="space-y-1.5">
              <PasswordInput
                label="비밀번호 확인"
                placeholder="비밀번호를 다시 입력해 주세요"
                autoComplete="new-password"
                required
                error={errors.passwordConfirm?.message}
                {...register("passwordConfirm")}
              />
              {passwordMatch === "match" && (
                <p className="text-xs text-status-success">✓ 비밀번호가 일치합니다</p>
              )}
              {passwordMatch === "mismatch" && (
                <p className="text-xs text-status-danger">비밀번호가 일치하지 않습니다</p>
              )}
            </div>

            {/* 이름 */}
            <Input
              label="이름"
              placeholder="홍길동"
              autoComplete="name"
              required
              error={errors.name?.message}
              {...register("name")}
            />

            {/* 휴대폰 번호 */}
            <div>
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
                    setValue("phone_number", formatted, {
                      shouldValidate: false,
                    });
                  },
                })}
              />
            </div>

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
          </div>

          {/* 동의 */}
          <div className="mt-6 space-y-3 p-4 bg-surface rounded-[12px]">
            <Checkbox
              label={
                <span>
                  <Link href="/terms" className="underline">이용약관</Link>에 동의합니다 (필수)
                </span>
              }
              required
              error={errors.agreeTerms?.message}
              {...register("agreeTerms")}
            />
            <Checkbox
              label={
                <span>
                  <Link href="/privacy" className="underline">개인정보 처리방침</Link>에 동의합니다 (필수)
                </span>
              }
              required
              error={errors.agreePrivacy?.message}
              {...register("agreePrivacy")}
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={isSubmitting}
            disabled={emailVerify !== "verified"}
            className="mt-6"
          >
            가입 완료
          </Button>
          {emailVerify !== "verified" && (
            <p className="mt-2 text-center text-xs text-text-secondary">
              가입을 완료하려면 이메일 본인 인증이 필요합니다
            </p>
          )}
        </form>

        <p className="mt-5 text-center text-sm text-text-secondary">
          이미 계정이 있으신가요?{" "}
          <Link
            href={ROUTES.LOGIN}
            className="font-semibold text-text-primary underline underline-offset-2"
          >
            로그인
          </Link>
        </p>
      </div>
    </SplitAuthShell>
  );
}
