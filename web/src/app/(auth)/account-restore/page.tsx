"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import DestructiveModal from "@/components/auth/DestructiveModal";
import { useToast } from "@/components/ui/Toast";
import { RESTORE_DATA_ITEMS, ROUTES } from "@/constants";
import type { RestoreDataKey } from "@/types";

/* =========================================
   이전 계정 발견 / 복원 페이지
   와이어프레임: mobile 09-A09 / desktop 14-A03
   ========================================= */

/* mock 이전 계정 데이터 */
const MOCK_PREVIOUS_ACCOUNT = {
  email: "j*********4@gmail.com",
  created_at: "2024.03.12",
  deleted_at: "2026.04.23",
  challenge_count: 42,
  points: 2840,
  pet_name: "함께",
  restore_deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
};

/* 카운트다운 훅 */
function useCountdown(deadline: string) {
  const [remaining, setRemaining] = useState<{
    days: number;
    hours: number;
    minutes: number;
  }>({ days: 0, hours: 0, minutes: 0 });

  useEffect(() => {
    const calc = () => {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) return setRemaining({ days: 0, hours: 0, minutes: 0 });
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setRemaining({ days, hours, minutes });
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

  const account = MOCK_PREVIOUS_ACCOUNT;
  const countdown = useCountdown(account.restore_deadline);

  /* 복원할 데이터 선택 */
  const [selectedKeys, setSelectedKeys] = useState<RestoreDataKey[]>(
    RESTORE_DATA_ITEMS.map((i) => i.key)
  );
  const toggleKey = (key: RestoreDataKey) => {
    setSelectedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  /* 파괴적 모달 */
  const [showDestructive, setShowDestructive] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [destroying, setDestroying] = useState(false);

  const handleRestore = async () => {
    setRestoring(true);
    try {
      // TODO(backend): /api/v1/auth/restore 엔드포인트 추가 필요
      showToast("계정 복원은 백엔드 추가 예정입니다", "info");
      router.push(ROUTES.HOME);
    } finally {
      setRestoring(false);
    }
  };

  const handleDestroy = async () => {
    setDestroying(true);
    try {
      // TODO(backend): /api/v1/auth/destroy-previous 엔드포인트 추가 필요
      showToast("기존 데이터 삭제 후 새로 시작합니다", "warning");
      setShowDestructive(false);
      router.push(ROUTES.SIGNUP);
    } finally {
      setDestroying(false);
    }
  };

  return (
    <SimpleAuthShell title="이전 계정 발견" backHref={ROUTES.LOGIN}>
      <div className="pt-4">
        {/* 경고 아이콘 + 헤더 */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-12 h-12 rounded-full bg-brand flex items-center justify-center flex-shrink-0">
            <span className="text-2xl" aria-hidden="true">📋</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-text-primary mb-1">
              이전에 사용하던 계정이 있어요
            </h2>
            <p className="text-sm text-text-secondary">
              {account.email}에서 가입했던 계정이 있습니다. 이전 데이터를 가져오거나 새로 시작할 수 있습니다.
            </p>
          </div>
        </div>

        {/* 데스크탑: 2단 카드 / 모바일: 1단 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* 이전 계정 정보 */}
          <div className="p-4 bg-surface rounded-[12px] space-y-3">
            <h3 className="text-sm font-semibold text-text-primary">
              이전 계정 정보
            </h3>

            <div className="grid grid-cols-2 gap-y-2 text-sm">
              <div>
                <p className="text-xs text-text-tertiary">가입일</p>
                <p className="font-medium">{account.created_at}</p>
              </div>
              <div>
                <p className="text-xs text-text-tertiary">탈퇴일</p>
                <p className="font-medium">{account.deleted_at}</p>
              </div>
              <div>
                <p className="text-xs text-text-tertiary">완료 챌린지</p>
                <p className="font-medium">{account.challenge_count}개</p>
              </div>
              <div>
                <p className="text-xs text-text-tertiary">포인트</p>
                <p className="font-medium">
                  {account.points.toLocaleString()} P
                </p>
              </div>
              <div>
                <p className="text-xs text-text-tertiary">캐릭터</p>
                <p className="font-medium">{account.pet_name}</p>
              </div>
            </div>

            {/* 복원 가능일 카운트다운 */}
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-text-tertiary mb-1">복원 가능 기간</p>
              <p className="text-sm font-semibold text-status-danger">
                {countdown.days}일 {countdown.hours}시간 {countdown.minutes}분 남음
              </p>
            </div>
          </div>

          {/* 복원할 데이터 선택 */}
          <div className="p-4 bg-surface rounded-[12px]">
            <h3 className="text-sm font-semibold text-text-primary mb-3">
              복원할 데이터 선택
            </h3>
            <div className="space-y-2.5">
              {RESTORE_DATA_ITEMS.map((item) => (
                <Checkbox
                  key={item.key}
                  label={item.label}
                  checked={selectedKeys.includes(item.key)}
                  onChange={() => toggleKey(item.key)}
                />
              ))}
            </div>
          </div>
        </div>

        {/* 주의 안내 */}
        <div className="p-4 bg-[#fffbe6] rounded-[12px] mb-6">
          <p className="text-xs text-[#7a6a00] leading-relaxed">
            <strong>⚠ 참고 사항</strong>
            <br />
            복원 시 SMS 인증이 필요합니다. &ldquo;새로 시작하기&rdquo; 선택 시 이전
            데이터가 영구적으로 삭제되어 복구할 수 없습니다. 선택 후 30일 이내 복원을 이용해 주세요.
          </p>
        </div>

        {/* 액션 버튼 */}
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
            disabled={selectedKeys.length === 0}
            onClick={handleRestore}
          >
            이전 정보 불러오기
          </Button>
        </div>
      </div>

      {/* 파괴적 확인 모달 */}
      <DestructiveModal
        open={showDestructive}
        onClose={() => setShowDestructive(false)}
        onConfirm={handleDestroy}
        loading={destroying}
      />
    </SimpleAuthShell>
  );
}
