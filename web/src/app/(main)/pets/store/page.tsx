"use client";

import Link from "next/link";
import { useState } from "react";
import { useStoreItems } from "@/hooks/queries/useStoreItems";
import { usePurchaseStoreItem } from "@/hooks/queries/usePurchaseStoreItem";
import { usePointBalance } from "@/hooks/queries/usePointBalance";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { ItemCategory, SpeciesLock, StoreItem } from "@/types/api";

/* =========================================
   상점 페이지
   - 전체 아이템을 한 번 조회 후 클라이언트 탭 필터링
   ========================================= */

type TabKey = "전체" | "사료" | "간식" | "비료/영양제" | "물" | "약";

const TAB_FILTER: Record<TabKey, ItemCategory[] | null> = {
  전체: null,
  사료: ["FOOD_ANIMAL", "FOOD_ANIMAL_PREMIUM"],
  간식: ["SNACK_ANIMAL"],
  "비료/영양제": ["FERTILIZER_PLANT", "FERTILIZER_PLANT_PREMIUM", "SUPPLEMENT_PLANT"],
  물: ["WATER"],
  약: ["MEDICINE"],
};

const TABS: TabKey[] = ["전체", "사료", "간식", "비료/영양제", "물", "약"];

const SPECIES_LABEL: Record<NonNullable<SpeciesLock>, string> = {
  DOG: "🐶 강아지",
  CAT: "🐱 고양이",
  PLANT: "🌱 식물",
};

function StoreItemCard({ item }: { item: StoreItem }) {
  const { mutate, isPending } = usePurchaseStoreItem();
  const { showToast } = useToast();

  function handlePurchase() {
    mutate(
      { item_id: item.id, quantity: 1 },
      {
        onSuccess: () => showToast(`${item.name} 1개 구매!`, "success"),
        onError: (err) => showToast(extractErrorMessage(err), "error"),
      }
    );
  }

  const speciesLabel =
    item.species_lock ? SPECIES_LABEL[item.species_lock] : "모두";

  return (
    <div className="bg-white border border-border rounded-[16px] p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-black text-text-primary leading-tight">{item.name}</p>
        <span className="shrink-0 text-[11px] bg-surface text-text-tertiary rounded-full px-2 py-0.5">
          {speciesLabel}
        </span>
      </div>
      {item.description && (
        <p className="text-xs text-text-secondary leading-relaxed">{item.description}</p>
      )}
      <div className="flex items-center justify-between mt-auto pt-1">
        <span className="text-sm font-semibold text-brand">{item.price.toLocaleString()} P</span>
        <button
          type="button"
          onClick={handlePurchase}
          disabled={isPending}
          className="px-3 py-1.5 bg-brand text-brand-black text-xs font-semibold rounded-[10px] disabled:opacity-50 hover:opacity-90 active:scale-95 transition-all"
        >
          {isPending ? "구매 중…" : "구매"}
        </button>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return <div className="h-24 bg-surface animate-pulse rounded-[16px]" />;
}

export default function StorePage() {
  const [activeTab, setActiveTab] = useState<TabKey>("전체");
  const { data, isLoading, isError } = useStoreItems();
  const { data: pointData } = usePointBalance(0);
  const { showToast: _showToast } = useToast();

  const allItems = data?.items ?? [];
  const filterCategories = TAB_FILTER[activeTab];
  const visibleItems = filterCategories
    ? allItems.filter((item) => filterCategories.includes(item.category))
    : allItems;

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/pets"
            className="text-sm text-text-secondary hover:text-text-primary transition-colors"
            aria-label="펫 화면으로 돌아가기"
          >
            ← 펫
          </Link>
          <h1 className="text-xl font-black text-text-primary">상점</h1>
        </div>
        {pointData !== undefined && (
          <span className="text-sm font-semibold text-brand">
            {pointData.balance.toLocaleString()} P
          </span>
        )}
      </div>

      {/* 카테고리 탭 */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={[
              "shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors",
              activeTab === tab
                ? "bg-brand text-brand-black"
                : "bg-surface text-text-secondary hover:bg-border",
            ].join(" ")}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 아이템 목록 */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {isError && (
        <div className="bg-status-danger-bg rounded-[14px] px-4 py-3">
          <p className="text-sm text-status-danger">아이템을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</p>
        </div>
      )}

      {!isLoading && !isError && visibleItems.length === 0 && (
        <div className="py-16 text-center">
          <p className="text-sm text-text-tertiary">아직 등록된 아이템이 없어요</p>
        </div>
      )}

      {!isLoading && !isError && visibleItems.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {visibleItems.map((item) => (
            <StoreItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
