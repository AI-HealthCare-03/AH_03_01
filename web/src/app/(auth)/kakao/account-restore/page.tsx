"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import DestructiveModal from "@/components/auth/DestructiveModal";
import { useToast } from "@/components/ui/Toast";
import { kakaoRestore, kakaoDestroy } from "@/lib/api/auth";
import { extractErrorMessage } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth";
import {
  ROUTES,
  KAKAO_RESTORE_TICKET_KEY,
  KAKAO_RESTORE_INFO_KEY,
} from "@/constants";

/* =========================================
   카카오 탈퇴 계정 복구 / 파기 페이지
   경로: /kakao/account-restore
   카카오 콜백에서 탈퇴 계정 감지 시 진입(restore_required).
   카카오 OAuth 로 이미 본인 확인을 마쳤으므로 별도 이메일 인증 없이
   복구 티켓만으로 복구/파기를 선택한다.
   ========================================= */

interface RestoreInfo {
  masked_email: string;
  deleted_at: string;
  restore_deadline: string;
}

function useCountdown(deadline?: string) {
  const [remaining, setRemaining] = useState({ days: 0, hours: 0, minutes: 0 });
  useEffect(() => {
    if (!deadline) return;
    const calc = () => {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) return setRemaining({ days: 0, hours: 0, minutes: 0 });
      setRemaining({
        days: Math.floor(diff / 86_400_000),
        hours: Math.floor((diff % 86_400_000) / 3_600_000),
        minutes: Math.floor((diff % 3_600_000) / 60_000),
      });
    };
    calc();
    const id = setInterval(calc, 60_000);
    return () => clearInterval(id);
  }, [deadline]);
  return remaining;
}

export default function KakaoAccountRestorePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const { setAuth } = useAuthStore();

  const [ticket, setTicket] = useState("");
  const [info, setInfo] = useState<RestoreInfo | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [destroying, setDestroying] = useState(false);
  const [showDestructive, setShowDestructive] = useState(false);

  const countdown = useCountdown(info?.restore_deadline);

  /* 진입 시 복구 티켓·정보 확인 — 없으면 로그인 화면으로 돌려보낸다 */
  useEffect(() => {
    const storedTicket = sessionStorage.getItem(KAKAO_RESTORE_TICKET_KEY);
    const storedInfo = sessionStorage.getItem(KAKAO_RESTORE_INFO_KEY);
    if (!storedTicket || !storedInfo) {
      router.replace(ROUTES.LOGIN);
      return;
    }
    try {
      setInfo(JSON.parse(storedInfo) as RestoreInfo);
      setTicket(storedTicket);
    } catch {
      router.replace(ROUTES.LOGIN);
    }
  }, [router]);

  const clearStorage = () => {
    sessionStorage.removeItem(KAKAO_RESTORE_TICKET_KEY);
    sessionStorage.removeItem(KAKAO_RESTORE_INFO_KEY);
  };

  const handleRestore = async () => {
    setRestoring(true);
    try {
      const { access_token } = await kakaoRestore(ticket);
      clearStorage();
      setAuth(access_token);
      showToast("계정을 복구했어요. 다시 오신 걸 환영해요!", "success");
      router.replace(ROUTES.HOME);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setRestoring(false);
    }
  };

  const handleDestroy = async () => {
    setDestroying(true);
    try {
      await kakaoDestroy(ticket);
      clearStorage();
      setShowDestructive(false);
      showToast("이전 데이터를 삭제했어요. 새로 시작할 수 있어요.", "success");
      router.replace(ROUTES.LOGIN);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setDestroying(false);
    }
  };

  if (!info) {
    return (
      <SimpleAuthShell title="이전 계정 발견" backHref={ROUTES.LOGIN}>
        <p className="pt-10 text-center text-sm text-text-secondary">불러오는 중…</p>
      </SimpleAuthShell>
    );
  }

  const expired = countdown.days === 0 && countdown.hours === 0 && countdown.minutes === 0;

  return (
    <SimpleAuthShell title="이전 계정 발견" backHref={ROUTES.LOGIN}>
      <div className="pt-4">
        <div className="flex items-start gap-4 mb-6">
          <div className="w-12 h-12 rounded-full bg-brand flex items-center justify-center flex-shrink-0">
            <span className="text-2xl" aria-hidden="true">📋</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-text-primary mb-1">이전에 사용하던 계정이 있어요</h2>
            <p className="text-sm text-text-secondary">
              {info.masked_email} 으로 탈퇴한 카카오 계정이 있습니다. 이전 데이터를 복구하거나 새로 시작할 수
              있어요.
            </p>
          </div>
        </div>

        {/* 이전 계정 정보 */}
        <div className="p-4 bg-surface rounded-[12px] mb-4">
          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <div>
              <p className="text-xs text-text-tertiary">탈퇴일</p>
              <p className="font-medium">{new Date(info.deleted_at).toLocaleDateString("ko-KR")}</p>
            </div>
            <div>
              <p className="text-xs text-text-tertiary">복원 가능 기간</p>
              <p className="font-semibold text-status-danger">
                {expired ? "기간 만료" : `${countdown.days}일 ${countdown.hours}시간 ${countdown.minutes}분 남음`}
              </p>
            </div>
          </div>
        </div>

        {/* 안내 */}
        <div className="p-4 bg-[#fffbe6] rounded-[12px] mb-6">
          <p className="text-xs text-[#7a6a00] leading-relaxed">
            <strong>⚠ 참고 사항</strong>
            <br />
            “새로 시작하기”를 선택하면 이전 데이터가 영구적으로 삭제되어 복구할 수 없어요. 복원은 탈퇴 후 30일
            이내에만 가능합니다.
          </p>
        </div>

        {/* 액션 */}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant="outline"
            size="lg"
            className="flex-1 order-2 sm:order-1"
            onClick={() => setShowDestructive(true)}
          >
            새로 시작하기
          </Button>
          <Button
            variant="primary"
            size="lg"
            className="flex-1 order-1 sm:order-2"
            loading={restoring}
            disabled={expired}
            onClick={handleRestore}
          >
            이전 정보 불러오기
          </Button>
        </div>
        {expired && (
          <p className="mt-2 text-center text-xs text-text-tertiary">
            복원 가능 기간이 지나 복구할 수 없어요. 새로 시작해 주세요.
          </p>
        )}
      </div>

      <DestructiveModal
        open={showDestructive}
        onClose={() => setShowDestructive(false)}
        onConfirm={handleDestroy}
        loading={destroying}
      />
    </SimpleAuthShell>
  );
}
