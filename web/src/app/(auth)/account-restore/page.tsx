"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import DestructiveModal from "@/components/auth/DestructiveModal";
import { useToast } from "@/components/ui/Toast";
import { ROUTES } from "@/constants";
import {
  checkEmailVerified,
  destroyPreviousAccount,
  getPreviousAccount,
  restoreAccount,
  sendEmailVerification,
} from "@/lib/api/auth";
import { extractErrorMessage } from "@/lib/api/client";
import type { PreviousAccount } from "@/types";

/* =========================================
   이전(탈퇴) 계정 발견 / 복구·파기 페이지
   회원가입에서 탈퇴 계정 감지 시 ?email= 로 진입.
   복구(전체)·파기 모두 이메일 본인 인증 필요.
   ========================================= */

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

export default function AccountRestorePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [email, setEmail] = useState("");

  const [account, setAccount] = useState<PreviousAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [verified, setVerified] = useState(false);
  const [sending, setSending] = useState(false);
  const [checking, setChecking] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [destroying, setDestroying] = useState(false);
  const [showDestructive, setShowDestructive] = useState(false);

  const countdown = useCountdown(account?.restore_deadline);

  /* 진입 시 탈퇴 계정 감지 — 없으면 가입 화면으로 돌려보낸다 */
  useEffect(() => {
    const stored = sessionStorage.getItem("restore_email");
    if (!stored) {
      router.replace(ROUTES.SIGNUP);
      return;
    }
    setEmail(stored);
    let active = true;
    getPreviousAccount(stored)
      .then((acc) => {
        if (!active) return;
        if (!acc) {
          showToast("복구할 수 있는 이전 계정이 없습니다.", "info");
          router.replace(ROUTES.SIGNUP);
          return;
        }
        setAccount(acc);
      })
      .catch((err) => active && showToast(extractErrorMessage(err), "error"))
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router, showToast]);

  const handleSendVerification = async () => {
    setSending(true);
    try {
      await sendEmailVerification(email);
      showToast("인증 메일을 보냈어요. 메일함에서 링크를 확인해 주세요.", "success");
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setSending(false);
    }
  };

  const handleCheckVerified = async () => {
    setChecking(true);
    try {
      const ok = await checkEmailVerified(email);
      setVerified(ok);
      showToast(
        ok ? "이메일 인증이 완료되었어요" : "아직 인증 전이에요. 메일의 링크를 클릭해 주세요.",
        ok ? "success" : "info",
      );
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setChecking(false);
    }
  };

  const handleRestore = async () => {
    setRestoring(true);
    try {
      await restoreAccount(email);
      showToast("계정을 복구했어요. 다시 로그인해 주세요.", "success");
      router.push(ROUTES.LOGIN);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setRestoring(false);
    }
  };

  const handleDestroy = async () => {
    setDestroying(true);
    try {
      await destroyPreviousAccount(email);
      showToast("이전 데이터를 삭제했어요. 새로 시작할 수 있어요.", "success");
      setShowDestructive(false);
      router.push(ROUTES.SIGNUP);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setDestroying(false);
    }
  };

  if (loading || !account) {
    return (
      <SimpleAuthShell title="이전 계정 발견" backHref={ROUTES.LOGIN}>
        <p className="pt-10 text-center text-sm text-text-secondary">불러오는 중…</p>
      </SimpleAuthShell>
    );
  }

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
              {account.masked_email} 으로 탈퇴한 계정이 있습니다. 본인 인증 후 이전 데이터를 복구하거나 새로
              시작할 수 있어요.
            </p>
          </div>
        </div>

        {/* 이전 계정 정보 */}
        <div className="p-4 bg-surface rounded-[12px] mb-4">
          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <div>
              <p className="text-xs text-text-tertiary">탈퇴일</p>
              <p className="font-medium">{new Date(account.deleted_at).toLocaleDateString("ko-KR")}</p>
            </div>
            <div>
              <p className="text-xs text-text-tertiary">복원 가능 기간</p>
              <p className="font-semibold text-status-danger">
                {countdown.days}일 {countdown.hours}시간 {countdown.minutes}분 남음
              </p>
            </div>
          </div>
        </div>

        {/* 이메일 본인 인증 */}
        <div className="p-4 bg-surface rounded-[12px] mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-text-primary">이메일 본인 인증</h3>
            {verified && <span className="text-xs font-semibold text-status-success">✓ 인증 완료</span>}
          </div>
          <p className="text-xs text-text-secondary mb-3">
            복구·파기는 본인 확인이 필요해요. 인증 메일의 링크를 클릭한 뒤 “인증 확인”을 눌러 주세요.
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              loading={sending}
              disabled={verified}
              onClick={handleSendVerification}
            >
              인증 메일 받기
            </Button>
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              loading={checking}
              disabled={verified}
              onClick={handleCheckVerified}
            >
              인증 확인
            </Button>
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
            disabled={!verified}
            onClick={() => setShowDestructive(true)}
          >
            새로 시작하기
          </Button>
          <Button
            variant="primary"
            size="lg"
            className="flex-1 order-1 sm:order-2"
            loading={restoring}
            disabled={!verified}
            onClick={handleRestore}
          >
            이전 정보 불러오기
          </Button>
        </div>
        {!verified && (
          <p className="mt-2 text-center text-xs text-text-tertiary">먼저 이메일 본인 인증을 완료해 주세요.</p>
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
