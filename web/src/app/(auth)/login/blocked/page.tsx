import Link from "next/link";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import { ROUTES } from "@/constants";

/* =========================================
   로그인 제한 화면 (5회 실패)
   와이어프레임: mobile 09-A07
   ========================================= */

export default function LoginBlockedPage() {
  return (
    <SimpleAuthShell title="로그인 제한">
      <div className="pt-8 text-center">
        {/* 경고 아이콘 */}
        <div className="flex justify-center mb-5">
          <div className="w-20 h-20 rounded-full bg-[#ffeaea] flex items-center justify-center">
            <span className="text-4xl" role="img" aria-label="경고">
              ⚠️
            </span>
          </div>
        </div>

        <h2 className="text-xl font-bold text-text-primary mb-3">
          로그인이 제한되었습니다
        </h2>
        <p className="text-sm text-text-secondary mb-8 leading-relaxed">
          비밀번호를 5회 이상 틀려 보안상 로그인이
          <br />
          일시적으로 제한되었습니다.
          <br />
          SMS 인증으로 본인 확인 후 이용해 주세요.
        </p>

        <div className="space-y-3">
          <Link href={ROUTES.SMS_VERIFY}>
            <Button variant="secondary" size="lg" fullWidth>
              SMS 인증하기
            </Button>
          </Link>
          <Link href={ROUTES.FORGOT_PASSWORD}>
            <Button variant="outline" size="lg" fullWidth>
              비밀번호 찾기
            </Button>
          </Link>
        </div>
      </div>
    </SimpleAuthShell>
  );
}
