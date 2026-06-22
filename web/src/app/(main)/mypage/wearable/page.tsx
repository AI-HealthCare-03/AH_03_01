"use client";

import Link from "next/link";
import { useToast } from "@/components/ui/Toast";

const DEVICES = [
  {
    icon: "⌚",
    brand: "Apple Watch",
    description: "Apple Health 연동 — 심박수, 걸음 수, 수면 데이터 자동 동기화",
  },
  {
    icon: "📱",
    brand: "Samsung Galaxy Watch",
    description: "Samsung Health 연동 — 혈압, 심박수, 활동량 자동 동기화",
  },
  {
    icon: "🏃",
    brand: "Garmin",
    description: "Garmin Connect 연동 — 운동 기록, 심박수, 수면 품질 자동 동기화",
  },
  {
    icon: "💪",
    brand: "Fitbit",
    description: "Fitbit 연동 — 걸음 수, 칼로리, 수면 단계 자동 동기화",
  },
  {
    icon: "📿",
    brand: "Xiaomi Mi Band",
    description: "Mi Fitness 연동 — 심박수, 혈중 산소, 활동량 자동 동기화",
  },
  {
    icon: "🔵",
    brand: "Withings",
    description: "Withings Health Mate 연동 — 체중, 혈압, 체성분 자동 동기화",
  },
] as const;

export default function WearablePage() {
  const { showToast } = useToast();

  function handleConnect() {
    showToast("서비스 준비중입니다.", "info");
  }

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Link href="/mypage" className="text-text-tertiary hover:text-text-primary text-lg">
          ←
        </Link>
        <h1 className="text-xl font-black text-text-primary">웨어러블 기기 연동</h1>
      </div>

      {/* 안내 배너 */}
      <section className="bg-brand rounded-[16px] px-5 py-4 space-y-1">
        <p className="text-sm font-bold text-brand-black">건강 데이터를 자동으로 기록하세요</p>
        <p className="text-xs text-brand-black/70">
          웨어러블 기기를 연동하면 걸음 수, 심박수, 수면 데이터가 건강 기록에 자동으로 반영돼요.
        </p>
      </section>

      {/* 기기 목록 */}
      <section className="bg-white border border-border rounded-[16px] overflow-hidden">
        <p className="text-xs font-bold text-text-tertiary px-5 pt-4 pb-2 uppercase tracking-wide">
          지원 예정 기기
        </p>
        <ul className="divide-y divide-border">
          {DEVICES.map((device) => (
            <li key={device.brand} className="flex items-center gap-4 px-5 py-4">
              <span aria-hidden="true" className="text-2xl shrink-0">{device.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-primary">{device.brand}</p>
                <p className="text-xs text-text-tertiary mt-0.5 leading-relaxed">
                  {device.description}
                </p>
              </div>
              <button
                type="button"
                onClick={handleConnect}
                className="shrink-0 px-3 py-1.5 border border-border rounded-[8px] text-xs font-semibold text-text-secondary hover:bg-surface transition-colors"
              >
                연동하기
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* 서비스 준비 중 안내 */}
      <section className="bg-white border border-border rounded-[16px] px-5 py-4 space-y-2">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-base">🛠️</span>
          <p className="text-sm font-bold text-text-primary">현재 개발 중인 기능이에요</p>
        </div>
        <p className="text-xs text-text-tertiary leading-relaxed">
          웨어러블 연동 기능은 현재 준비 중입니다. 출시되면 공지로 안내해 드릴게요.
        </p>
      </section>
    </div>
  );
}
