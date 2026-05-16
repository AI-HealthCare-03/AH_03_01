"use client";

import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

/* =========================================
   보상·인증 안내 팝업 (10-C20 / 15-C05)
   어디서든 진입 가능한 공통 모달
   ========================================= */

interface ChallengeRewardGuideModalProps {
  open: boolean;
  onClose: () => void;
}

export default function ChallengeRewardGuideModal({
  open,
  onClose,
}: ChallengeRewardGuideModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="보상 & 인증 안내" maxWidth="md">
      <div className="px-6 py-5 space-y-5">
        {/* 개인 보상 */}
        <section>
          <h3 className="text-sm font-bold text-text-primary mb-2">
            개인 챌린지 보상
          </h3>
          <div className="rounded-[12px] border border-border overflow-hidden text-sm">
            <table className="w-full">
              <thead className="bg-surface">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-text-secondary">
                    보상 종류
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-semibold text-text-secondary">
                    포인트
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-border">
                  <td className="px-3 py-2 text-text-primary">데일리 인증</td>
                  <td className="px-3 py-2 text-right font-semibold text-brand-black">
                    50 ~ 100 P
                  </td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-2 text-text-primary">기간 완주</td>
                  <td className="px-3 py-2 text-right font-semibold text-brand-black">
                    200 P
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* 그룹 보상 */}
        <section>
          <h3 className="text-sm font-bold text-text-primary mb-2">
            그룹 챌린지 보상
          </h3>
          <div className="rounded-[12px] border border-border overflow-hidden text-sm">
            <table className="w-full">
              <thead className="bg-surface">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-text-secondary">
                    보상 종류
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-semibold text-text-secondary">
                    포인트
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-border">
                  <td className="px-3 py-2 text-text-primary">데일리 인증</td>
                  <td className="px-3 py-2 text-right font-semibold text-brand-black">
                    70 ~ 100 P
                  </td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-2 text-text-primary">그룹 전체 완주</td>
                  <td className="px-3 py-2 text-right font-semibold text-brand-black">
                    500 P
                  </td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-2 text-text-primary">개인 기간 완주</td>
                  <td className="px-3 py-2 text-right font-semibold text-brand-black">
                    200 P
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* 인증 방식 */}
        <section>
          <h3 className="text-sm font-bold text-text-primary mb-2">인증 방식</h3>
          <div className="space-y-2">
            <div className="flex gap-3 items-start p-3 bg-surface rounded-[10px]">
              <span className="text-xl" aria-hidden="true">✅</span>
              <div>
                <p className="text-sm font-semibold text-text-primary">
                  체크 인증
                </p>
                <p className="text-xs text-text-secondary">
                  금주, 수면, 명상 — 예/아니오 버튼으로 간편 인증
                </p>
              </div>
            </div>
            <div className="flex gap-3 items-start p-3 bg-surface rounded-[10px]">
              <span className="text-xl" aria-hidden="true">📸</span>
              <div>
                <p className="text-sm font-semibold text-text-primary">
                  사진 인증
                </p>
                <p className="text-xs text-text-secondary">
                  운동, 물 마시기, 식습관, 금연, 질환 관리 — 사진으로 AI 검증
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 실패방지권 */}
        <section>
          <h3 className="text-sm font-bold text-text-primary mb-2">
            실패 방지권
          </h3>
          <div className="flex gap-3 items-start p-3 bg-surface rounded-[10px]">
            <span className="text-xl" aria-hidden="true">🛡️</span>
            <div>
              <p className="text-sm font-semibold text-text-primary">
                실패 방지권
              </p>
              <p className="text-xs text-text-secondary">
                하루 인증을 놓쳤을 때 방지권을 사용하면 실패 처리 없이
                연속을 유지할 수 있어요. 마이펫 보상 등으로 획득 가능해요.
              </p>
            </div>
          </div>
        </section>

        <Button variant="primary" size="md" fullWidth onClick={onClose}>
          확인
        </Button>
      </div>
    </Modal>
  );
}
