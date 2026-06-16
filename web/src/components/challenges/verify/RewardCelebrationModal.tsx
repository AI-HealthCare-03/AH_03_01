"use client";

import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

/* =========================================
   인증 성공 보상 모달 (10-C13/C14/C15)
   ========================================= */

interface RewardCelebrationModalProps {
  open: boolean;
  onClose: () => void;
  onShare?: () => void;
  rewardType?: "daily" | "period" | "group";
  earnedPoints?: number | null;
}

export default function RewardCelebrationModal({
  open,
  onClose,
  onShare,
  rewardType = "daily",
  earnedPoints,
}: RewardCelebrationModalProps) {
  const content = {
    daily: {
      emoji: "🎉",
      title: "인증 완료!",
      subtitle: "오늘도 훌륭해요!",
      points: earnedPoints ?? 100,
      desc: "데일리 인증 보상",
    },
    period: {
      emoji: "🏆",
      title: "챌린지 완주!",
      subtitle: "끝까지 해내셨어요!",
      points: 200,
      desc: "기간 완주 보너스",
    },
    group: {
      emoji: "🥇",
      title: "그룹 챌린지 완주!",
      subtitle: "모두가 해냈어요!",
      points: 500,
      desc: "그룹 완주 보너스",
    },
  }[rewardType];

  return (
    <Modal open={open} onClose={onClose} maxWidth="sm">
      <div className="px-6 py-8 text-center">
        <p className="text-6xl mb-4" aria-hidden="true">
          {content.emoji}
        </p>
        <h2 className="text-xl font-black text-text-primary mb-1">
          {content.title}
        </h2>
        <p className="text-sm text-text-secondary mb-6">{content.subtitle}</p>

        {/* 포인트 */}
        <div className="bg-brand rounded-[14px] px-8 py-5 mb-6 inline-block w-full">
          <p className="text-xs font-semibold text-brand-black/60 mb-1">
            {content.desc}
          </p>
          <p className="text-3xl font-black text-brand-black">
            +{content.points} P
          </p>
          <p className="text-xs text-brand-black/50 mt-1">
            실제 포인트는 내 지갑에서 확인하세요
          </p>
        </div>

        <div className="flex flex-col gap-2">
          {onShare && (
            <Button variant="outline" size="md" fullWidth onClick={onShare}>
              자랑하기
            </Button>
          )}
          <Button variant="primary" size="md" fullWidth onClick={onClose}>
            확인
          </Button>
        </div>
      </div>
    </Modal>
  );
}
