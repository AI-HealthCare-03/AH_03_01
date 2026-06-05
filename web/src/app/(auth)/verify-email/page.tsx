"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import { verifyEmailToken } from "@/lib/api/auth";
import { ROUTES } from "@/constants";

/* =========================================
   이메일 인증 랜딩 페이지
   메일 링크({FRONTEND_BASE_URL}/verify-email?token=...) 로 진입 시
   토큰을 검증해 본인 인증을 완료한다.
   ========================================= */

type Status = "loading" | "success" | "error";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<Status>("loading");
  const calledRef = useRef(false);

  useEffect(() => {
    // 토큰은 1회용 — StrictMode 의 effect 이중 호출로 2번째가 실패 처리되는 것을 방지
    if (calledRef.current) return;
    calledRef.current = true;

    if (!token) {
      setStatus("error");
      return;
    }
    verifyEmailToken(token)
      .then(() => setStatus("success"))
      .catch(() => setStatus("error"));
  }, [token]);

  return (
    <SimpleAuthShell title="이메일 인증" backHref={ROUTES.LOGIN}>
      <div className="pt-6 text-center">
        {status === "loading" && (
          <p className="text-sm text-text-secondary">이메일 인증을 확인하고 있어요…</p>
        )}

        {status === "success" && (
          <>
            <p className="text-lg font-semibold text-text-primary mb-2">
              ✓ 이메일 인증이 완료되었어요!
            </p>
            <p className="text-sm text-text-secondary">
              작성하던 가입 페이지로 돌아가 &quot;인증 완료 확인&quot; 버튼을 눌러
              가입을 계속 진행해 주세요.
            </p>
            <p className="mt-3 text-xs text-text-tertiary">이 창은 닫으셔도 됩니다.</p>
          </>
        )}

        {status === "error" && (
          <>
            <p className="text-lg font-semibold text-text-primary mb-2">인증할 수 없어요</p>
            <p className="text-sm text-text-secondary mb-8">
              유효하지 않거나 만료된 링크예요. 가입 화면에서 인증 메일을 다시 받아 주세요.
            </p>
            <Link href={ROUTES.SIGNUP}>
              <Button variant="outline" size="lg" fullWidth>
                가입 화면으로
              </Button>
            </Link>
          </>
        )}
      </div>
    </SimpleAuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
