"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import SimpleAuthShell from "@/components/layout/SimpleAuthShell";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Checkbox from "@/components/ui/Checkbox";
import { useToast } from "@/components/ui/Toast";
import { WITHDRAWAL_REASONS, ROUTES } from "@/constants";

/* =========================================
   회원탈퇴 페이지
   와이어프레임: mobile 09-A08
   ========================================= */

export default function WithdrawalPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [selectedReason, setSelectedReason] = useState<string | null>(null);
  const [otherText, setOtherText] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);

  const isOther = selectedReason === "기타";
  const canSubmit =
    selectedReason !== null &&
    (isOther ? otherText.trim().length > 0 : true);

  const handleWithdraw = async () => {
    setLoading(true);
    try {
      // TODO(backend): DELETE /api/v1/users/me 엔드포인트 확인 필요
      showToast("탈퇴 처리는 백엔드 추가 예정입니다", "info");
      setConfirmOpen(false);
      router.push(ROUTES.LOGIN);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SimpleAuthShell title="회원탈퇴" backHref="/mypage">
      <div className="pt-4">
        <h2 className="text-xl font-bold text-text-primary mb-2">
          탈퇴 이유를 알려주세요
        </h2>
        <p className="text-sm text-text-secondary mb-6">
          더 나은 서비스를 위해 소중한 의견을 남겨주세요. 항상 감사합니다.
        </p>

        {/* 이유 라디오 목록 */}
        <div className="space-y-2.5 mb-5">
          {WITHDRAWAL_REASONS.map((reason) => (
            <label
              key={reason}
              className={[
                "flex items-center gap-3 p-3.5 rounded-[12px] border cursor-pointer transition-colors",
                selectedReason === reason
                  ? "border-brand-black bg-surface"
                  : "border-border hover:border-text-tertiary",
              ].join(" ")}
            >
              <input
                type="radio"
                name="withdrawal-reason"
                value={reason}
                checked={selectedReason === reason}
                onChange={() => setSelectedReason(reason)}
                className="sr-only"
              />
              {/* 커스텀 라디오 */}
              <span
                className={[
                  "w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center",
                  selectedReason === reason
                    ? "border-brand-black"
                    : "border-border",
                ].join(" ")}
                aria-hidden="true"
              >
                {selectedReason === reason && (
                  <span className="w-2.5 h-2.5 rounded-full bg-brand-black" />
                )}
              </span>
              <span className="text-sm text-text-primary">{reason}</span>
            </label>
          ))}
        </div>

        {/* 자유의견 (기타 선택 시) */}
        {isOther && (
          <textarea
            placeholder="탈퇴 이유를 자세히 적어주세요"
            value={otherText}
            onChange={(e) => setOtherText(e.target.value)}
            maxLength={300}
            rows={4}
            className="w-full p-4 border border-border rounded-[12px] text-sm resize-none focus:outline-none focus:border-brand-black mb-5"
            aria-label="기타 탈퇴 이유"
          />
        )}

        {/* 버튼 */}
        <div className="flex flex-col gap-3">
          <Button
            variant="danger"
            size="lg"
            fullWidth
            disabled={!canSubmit}
            onClick={() => setConfirmOpen(true)}
          >
            탈퇴하기
          </Button>
          <Button
            variant="outline"
            size="lg"
            fullWidth
            onClick={() => router.back()}
          >
            유지하기
          </Button>
        </div>
      </div>

      {/* 탈퇴 최종 확인 모달 */}
      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <div className="p-6">
          <h3 className="text-lg font-bold text-text-primary mb-2">
            정말 탈퇴하시겠습니까?
          </h3>
          <p className="text-sm text-text-secondary mb-5 leading-relaxed">
            탈퇴하시면 모든 건강 기록, 챌린지 진행 상황, 포인트 등이 삭제됩니다.
            30일 이내에는 계정 복원이 가능합니다.
          </p>
          <div className="mb-6">
            <Checkbox
              label="위 내용을 확인했으며 탈퇴에 동의합니다"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              onClick={() => setConfirmOpen(false)}
            >
              취소
            </Button>
            <Button
              variant="danger"
              size="md"
              className="flex-1"
              disabled={!agreed}
              loading={loading}
              onClick={handleWithdraw}
            >
              탈퇴하기
            </Button>
          </div>
        </div>
      </Modal>
    </SimpleAuthShell>
  );
}
