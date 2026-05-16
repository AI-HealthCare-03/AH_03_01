"use client";

import Modal from "@/components/ui/Modal";

interface ExerciseDetailModalProps {
  open: boolean;
  onClose: () => void;
}

export default function ExerciseDetailModal({ open, onClose }: ExerciseDetailModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="운동 권고 자세히" maxWidth="lg">
      <div className="px-6 pb-6 pt-4 space-y-5 max-h-[70vh] overflow-y-auto">
        {/* 운동 처방 표 */}
        <section>
          <h3 className="font-bold text-sm text-text-primary mb-2">권장 운동 처방</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border border-border rounded-[8px] overflow-hidden">
              <thead>
                <tr className="bg-surface">
                  <th className="p-2 text-left font-semibold text-text-secondary border-b border-border">항목</th>
                  <th className="p-2 text-left font-semibold text-text-secondary border-b border-border">유산소</th>
                  <th className="p-2 text-left font-semibold text-text-secondary border-b border-border">근력</th>
                </tr>
              </thead>
              <tbody className="text-text-primary">
                {[
                  { item: "빈도", aerobic: "주 5일 이상", strength: "주 2~3일" },
                  { item: "강도", aerobic: "중강도 (RPE 12~13)", strength: "중강도 (1RM 60~70%)" },
                  { item: "시간", aerobic: "1회 30분 이상", strength: "1회 20~30분" },
                  { item: "목표", aerobic: "주 150분 이상", strength: "8~12회 × 2~3세트" },
                ].map((row, i) => (
                  <tr key={i} className={i % 2 === 1 ? "bg-surface/50" : ""}>
                    <td className="p-2 font-medium">{row.item}</td>
                    <td className="p-2">{row.aerobic}</td>
                    <td className="p-2">{row.strength}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* 추천 운동 종류 */}
        <section>
          <h3 className="font-bold text-sm text-text-primary mb-2">추천 운동 종류</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { icon: "🚶", name: "빠르게 걷기", sub: "혈압 조절에 탁월" },
              { icon: "🚴", name: "자전거 타기", sub: "관절 부담 낮음" },
              { icon: "🏊", name: "수영", sub: "혈압·혈당 동시 개선" },
              { icon: "🧘", name: "요가/스트레칭", sub: "혈압 완화 효과" },
            ].map((e) => (
              <div
                key={e.name}
                className="flex items-center gap-2 p-3 bg-surface rounded-[10px]"
              >
                <span className="text-2xl">{e.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-text-primary">{e.name}</p>
                  <p className="text-xs text-text-tertiary">{e.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 주의사항 */}
        <section>
          <h3 className="font-bold text-sm text-text-primary mb-2">주의사항</h3>
          <ul className="space-y-1 text-xs text-text-secondary list-disc list-inside">
            <li>혈압 160/100 mmHg 이상 시 격렬한 운동 전 의사와 상담</li>
            <li>운동 중 흉통·호흡곤란·어지럼증 발생 시 즉시 중단</li>
            <li>충분한 준비운동(5~10분) 및 정리운동 필수</li>
            <li>혈당 70 mg/dL 미만 시 운동 전 탄수화물 섭취 필요</li>
          </ul>
        </section>

        {/* 임상 근거 */}
        <section className="bg-[#e3f2fd] rounded-[10px] p-3">
          <h3 className="font-bold text-xs text-status-info mb-1">임상 근거</h3>
          <p className="text-xs text-text-secondary">
            KSH 2022 고혈압 진료지침 — 유산소 운동 주 150분은 수축기 혈압을
            평균 5~8 mmHg 낮추는 효과가 있습니다. (근거 수준 A)
          </p>
        </section>

        {/* 면책 */}
        <p className="text-[11px] text-text-tertiary">
          본 내용은 의학적 진단이나 처방이 아닙니다. 개인 상태에 따라 다를 수 있으니
          반드시 의료 전문가와 상담하세요.
        </p>
      </div>
    </Modal>
  );
}
