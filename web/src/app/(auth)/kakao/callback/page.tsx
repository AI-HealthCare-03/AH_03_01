"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import { useToast } from "@/components/ui/Toast";
import { kakaoCallback } from "@/lib/api/auth";
import { useAuthStore } from "@/stores/auth";
import { ROUTES, KAKAO_STATE_KEY, KAKAO_TICKET_KEY, KAKAO_PREFILL_KEY } from "@/constants";

/* =========================================
   카카오 OAuth 콜백 페이지
   경로: /kakao/callback
   백엔드 KAKAO_REDIRECT_URI 와 일치해야 함
   ========================================= */

function KakaoCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setAuth } = useAuthStore();
  const { showToast } = useToast();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const stateFromUrl = searchParams.get("state");

    if (!code || !stateFromUrl) {
      setErrorMsg("잘못된 접근입니다. 카카오 인증 파라미터가 없습니다.");
      return;
    }

    const savedState = sessionStorage.getItem(KAKAO_STATE_KEY);
    if (!savedState || savedState !== stateFromUrl) {
      setErrorMsg("보안 검증에 실패했습니다. 다시 시도해 주세요.");
      return;
    }

    let active = true;

    kakaoCallback(code, stateFromUrl)
      .then((res) => {
        if (!active) return;

        if (res.status === "login") {
          sessionStorage.removeItem(KAKAO_STATE_KEY);
          setAuth(res.access_token);
          router.replace(ROUTES.HOME);
          return;
        }

        /* signup_required: 추가 정보 입력 화면으로 이동 */
        sessionStorage.removeItem(KAKAO_STATE_KEY);
        sessionStorage.setItem(KAKAO_TICKET_KEY, res.signup_ticket);
        sessionStorage.setItem(KAKAO_PREFILL_KEY, JSON.stringify(res.prefill));
        router.replace(ROUTES.KAKAO_COMPLETE_SIGNUP);
      })
      .catch((err) => {
        if (!active) return;
        const status = (err as { response?: { status?: number } }).response?.status;

        if (status === 401) {
          setErrorMsg("이용이 제한된 계정입니다. 고객센터에 문의해 주세요.");
          return;
        }
        if (status === 403) {
          /* 탈퇴 후 복구 가능한 계정 */
          showToast("탈퇴한 계정입니다. 계정 복구 페이지로 이동합니다.", "info");
          router.replace(ROUTES.ACCOUNT_RESTORE);
          return;
        }
        setErrorMsg("카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.");
      });

    return () => {
      active = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (errorMsg) {
    return (
      <SimpleAuthShell title="카카오 로그인" backHref={ROUTES.LOGIN}>
        <div className="pt-10 flex flex-col items-center gap-6">
          <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center">
            <span className="text-2xl" aria-hidden="true">!</span>
          </div>
          <p className="text-sm text-center text-text-secondary">{errorMsg}</p>
          <a
            href={ROUTES.LOGIN}
            className="text-sm font-semibold text-text-primary underline underline-offset-2"
          >
            로그인 화면으로 돌아가기
          </a>
        </div>
      </SimpleAuthShell>
    );
  }

  return (
    <SimpleAuthShell title="카카오 로그인">
      <div className="pt-16 flex flex-col items-center gap-4">
        <span
          className="w-10 h-10 border-4 border-[#FEE500] border-t-transparent rounded-full animate-spin"
          aria-hidden="true"
        />
        <p className="text-sm text-text-secondary">카카오 계정을 확인하는 중입니다...</p>
      </div>
    </SimpleAuthShell>
  );
}

export default function KakaoCallbackPage() {
  return (
    <Suspense
      fallback={
        <SimpleAuthShell title="카카오 로그인">
          <div className="pt-16 flex flex-col items-center gap-4">
            <span
              className="w-10 h-10 border-4 border-[#FEE500] border-t-transparent rounded-full animate-spin"
              aria-hidden="true"
            />
            <p className="text-sm text-text-secondary">로딩 중...</p>
          </div>
        </SimpleAuthShell>
      }
    >
      <KakaoCallbackInner />
    </Suspense>
  );
}
