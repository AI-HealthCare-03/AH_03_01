"use client";

import { useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import { DESTRUCT_ITEMS } from "@/constants";

/* =========================================
   파괴적 액션 확인 모달
   와이어프레임: mobile 09-A10 / desktop 14-A04
   동의 체크박스가 켜져야 "새로 시작" 버튼 활성화
   ========================================= */

interface DestructiveModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
}

export default function DestructiveModal({
  open,
  onClose,
  onConfirm,
  loading = false,
}: DestructiveModalProps) {
  const [agreed, setAgreed] = useState(false);

  const handleClose = () => {
    setAgreed(false);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} maxWidth="sm">
      <div className="p-6">
        {/* 경고 아이콘 */}
        <div className="flex justify-center mb-4">
          <div className="w-14 h-14 rounded-full bg-[#fffbe6] flex items-center justify-center">
            <span className="text-3xl" aria-hidden="true">⚠️</span>
          </div>
        </div>

        {/* 제목 */}
        <h3 className="text-lg font-bold text-text-primary text-center mb-2">
          이전 데이터를 영구 삭제할까요?
        </h3>
        <p className="text-sm text-text-secondary text-center mb-5">
          새로 시작하시면 이전 데이터가 <strong>영구적으로 삭제</strong>되어
          복구할 수 없습니다
        </p>

        {/* 삭제될 항목 목록 */}
        <div className="bg-surface rounded-[12px] p-4 mb-5 space-y-2">
          {DESTRUCT_ITEMS.map((item) => (
            <div key={item.label} className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">{item.label}</span>
              <span className="text-sm font-medium text-text-primary">
                {item.value}
              </span>
            </div>
          ))}
        </div>

        {/* 동의 체크박스 */}
        <div className="mb-6">
          <Checkbox
            label="위 내용을 확인했으며 영구 삭제에 동의합니다"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
          />
        </div>

        {/* 액션 버튼 */}
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="md"
            className="flex-1"
            onClick={handleClose}
          >
            취소
          </Button>
          <Button
            variant="danger"
            size="md"
            className="flex-1"
            disabled={!agreed}
            loading={loading}
            onClick={onConfirm}
          >
            새로 시작
          </Button>
        </div>
      </div>
    </Modal>
  );
}
