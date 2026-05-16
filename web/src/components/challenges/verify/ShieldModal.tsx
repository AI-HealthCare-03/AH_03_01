"use client";

import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

/* =========================================
   실패 방지권 사용 모달 (10-C12)
   shield_inventory_id: 현재 mock 1
   ========================================= */

interface ShieldModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
}

export default function ShieldModal({
  open,
  onClose,
  onConfirm,
  loading = false,
}: ShieldModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="실패 방지권 사용" maxWidth="sm">
      <div className="px-6 py-5">
        <div className="flex flex-col items-center text-center mb-6">
          <p className="text-5xl mb-3" aria-hidden="true">
            🛡️
          </p>
          <p className="text-sm text-text-secondary leading-relaxed">
            실패 방지권을 사용하면 오늘 인증을 놓쳐도
            <br />
            챌린지 연속 기록이 유지돼요.
          </p>
          <p className="text-xs text-text-tertiary mt-2">
            * 방지권 1개가 차감됩니다
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="md"
            fullWidth
            onClick={onClose}
            disabled={loading}
          >
            취소
          </Button>
          <Button
            variant="secondary"
            size="md"
            fullWidth
            onClick={onConfirm}
            loading={loading}
          >
            방지권 사용
          </Button>
        </div>
      </div>
    </Modal>
  );
}
