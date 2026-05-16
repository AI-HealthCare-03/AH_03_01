import { z } from "zod";

/* 이메일 */
export const emailSchema = z
  .string()
  .min(1, "이메일을 입력해 주세요")
  .email("올바른 이메일 형식을 입력해 주세요");

/* 비밀번호 */
export const passwordSchema = z
  .string()
  .min(8, "비밀번호는 8자 이상이어야 합니다")
  .max(72, "비밀번호는 72자 이하여야 합니다")
  .regex(/[A-Za-z]/, "영문자를 포함해야 합니다")
  .regex(/[0-9]/, "숫자를 포함해야 합니다");

/* 이름 */
export const nameSchema = z
  .string()
  .min(2, "이름은 2자 이상 입력해 주세요")
  .max(20, "이름은 20자 이하여야 합니다");

/* 닉네임 */
export const nicknameSchema = z
  .string()
  .min(2, "닉네임은 2자 이상 입력해 주세요")
  .max(15, "닉네임은 15자 이하여야 합니다")
  .regex(/^[가-힣a-zA-Z0-9_]+$/, "한글, 영문, 숫자, 밑줄만 사용할 수 있습니다");

/* 휴대폰 번호 */
export const phoneSchema = z
  .string()
  .regex(/^010-?\d{4}-?\d{4}$/, "올바른 휴대폰 번호를 입력해 주세요 (010-XXXX-XXXX)");

/* 생년월일 */
export const birthDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "YYYY-MM-DD 형식으로 입력해 주세요")
  .refine((val) => {
    const date = new Date(val);
    if (isNaN(date.getTime())) return false;
    const now = new Date();
    const minDate = new Date("1900-01-01");
    return date >= minDate && date <= now;
  }, "올바른 생년월일을 입력해 주세요");

/* 성별 */
export const genderSchema = z.enum(["MALE", "FEMALE"], {
  error: "성별을 선택해 주세요",
});

/* SMS 인증 코드 */
export const smsCodeSchema = z
  .string()
  .length(6, "6자리 인증코드를 입력해 주세요")
  .regex(/^\d{6}$/, "숫자만 입력해 주세요");

/* ==== 폼 스키마 ==== */

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "비밀번호를 입력해 주세요"),
  rememberMe: z.boolean().optional(),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const signupSchema = z
  .object({
    email: emailSchema,
    nickname: nicknameSchema,
    password: passwordSchema,
    passwordConfirm: z.string().min(1, "비밀번호 확인을 입력해 주세요"),
    name: nameSchema,
    phone_number: phoneSchema,
    birth_date: birthDateSchema,
    gender: genderSchema,
    agreeTerms: z.literal(true, {
      error: "이용약관에 동의해 주세요",
    }),
    agreePrivacy: z.literal(true, {
      error: "개인정보 처리방침에 동의해 주세요",
    }),
  })
  .refine((data) => data.password === data.passwordConfirm, {
    message: "비밀번호가 일치하지 않습니다",
    path: ["passwordConfirm"],
  });
export type SignupFormValues = z.infer<typeof signupSchema>;

export const forgotIdSchema = z.object({
  name: nameSchema,
  phone_number: phoneSchema,
});
export type ForgotIdFormValues = z.infer<typeof forgotIdSchema>;

export const forgotPasswordSchema = z
  .object({
    email: emailSchema,
    phone_number: phoneSchema,
    new_password: passwordSchema,
    new_password_confirm: z.string().min(1, "비밀번호 확인을 입력해 주세요"),
  })
  .refine((data) => data.new_password === data.new_password_confirm, {
    message: "비밀번호가 일치하지 않습니다",
    path: ["new_password_confirm"],
  });
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

/* 비밀번호 강도 계산 */
export function getPasswordStrength(
  password: string
): "weak" | "fair" | "strong" {
  if (password.length < 8) return "weak";
  let score = 0;
  if (/[a-z]/.test(password)) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;
  if (password.length >= 12) score++;
  if (score <= 2) return "weak";
  if (score <= 3) return "fair";
  return "strong";
}

/* 전화번호 자동 포매팅 */
export function formatPhoneNumber(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length <= 3) return digits;
  if (digits.length <= 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7, 11)}`;
}
