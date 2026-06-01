"use client";

import Link from "next/link";
import { useInventory } from "@/hooks/queries/useInventory";
import { useUseInventoryItem } from "@/hooks/queries/useUseInventoryItem";
import { useToast } from "@/components/ui/Toast";
import { extractErrorMessage } from "@/lib/api/client";
import type { InventoryItem, ItemCategory } from "@/types/api";

/* =========================================
   가방(인벤토리) 페이지
   - 전체 조회 후 카테고리별 클라이언트 그룹화
   ========================================= */

type GroupKey = "약/물" | "사료/간식" | "비료/영양제" | "배경" | "가구/소품" | "꾸미기" | "티켓";

const GROUP_CATEGORIES: Record<GroupKey, ItemCategory[]> = {
  "약/물": ["MEDICINE", "WATER"],
  "사료/간식": ["FOOD_ANIMAL", "FOOD_ANIMAL_PREMIUM", "SNACK_ANIMAL"],
  "비료/영양제": ["FERTILIZER_PLANT", "FERTILIZER_PLANT_PREMIUM", "SUPPLEMENT_PLANT"],
  배경: ["BACKGROUND"],
  "가구/소품": ["FURNITURE"],
  꾸미기: ["DECORATION", "PET"],
  티켓: ["TICKET"],
};

const GROUP_KEYS: GroupKey[] = ["약/물", "사료/간식", "비료/영양제", "배경", "가구/소품", "꾸미기", "티켓"];

function groupItems(items: InventoryItem[]): Record<GroupKey, InventoryItem[]> {
  const result = {} as Record<GroupKey, InventoryItem[]>;
  for (const key of GROUP_KEYS) {
    result[key] = items.filter((item) => GROUP_CATEGORIES[key].includes(item.category));
  }
  return result;
}

function InventoryRow({ item }: { item: InventoryItem }) {
  const { mutate, isPending } = useUseInventoryItem();
  const { showToast } = useToast();
  const isEmpty = item.quantity === 0;

  function handleUse() {
    mutate(item.id, {
      onSuccess: (data) => showToast(data.message, "success"),
      onError: (err) => showToast(extractErrorMessage(err), "error"),
    });
  }

  return (
    <div
      className={[
        "flex items-center justify-between px-4 py-3 rounded-[14px] border border-border",
        isEmpty ? "opacity-50 bg-surface" : "bg-white",
      ].join(" ")}
    >
      <div className="flex items-center gap-3 min-w-0">
        {item.asset && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={item.asset} alt="" className="w-10 h-10 object-contain shrink-0" draggable={false} />
        )}
        <div className="min-w-0">
          <p className={["text-sm font-semibold", isEmpty ? "text-text-tertiary" : "text-text-primary"].join(" ")}>
            {item.name}
          </p>
          <p className="text-xs text-text-tertiary">수량 {item.quantity}개</p>
        </div>
      </div>
      <button
        type="button"
        onClick={handleUse}
        disabled={isEmpty || isPending}
        className="px-3 py-1.5 bg-brand text-brand-black text-xs font-semibold rounded-[10px] disabled:opacity-40 hover:opacity-90 active:scale-95 transition-all"
      >
        {isPending ? "사용 중…" : "사용"}
      </button>
    </div>
  );
}

function SkeletonRow() {
  return <div className="h-14 bg-surface animate-pulse rounded-[14px]" />;
}

export default function InventoryPage() {
  const { data, isLoading, isError } = useInventory();
  const allItems = data?.items ?? [];
  const grouped = groupItems(allItems);
  const isEmpty = !isLoading && !isError && allItems.length === 0;

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Link
          href="/pets"
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
          aria-label="펫 화면으로 돌아가기"
        >
          ← 펫
        </Link>
        <h1 className="text-xl font-black text-text-primary">가방</h1>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
        </div>
      )}

      {/* 에러 */}
      {isError && (
        <div className="bg-status-danger-bg rounded-[14px] px-4 py-3">
          <p className="text-sm text-status-danger">인벤토리를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</p>
        </div>
      )}

      {/* 빈 상태 */}
      {isEmpty && (
        <div className="py-16 text-center space-y-4">
          <p className="text-sm text-text-tertiary">가방이 비어 있어요. 상점에서 아이템을 구매해 보세요.</p>
          <Link
            href="/pets/store"
            className="inline-block px-5 py-2 bg-brand text-brand-black text-sm font-semibold rounded-[12px] hover:opacity-90 transition-opacity"
          >
            상점 가기
          </Link>
        </div>
      )}

      {/* 그룹별 목록 */}
      {!isLoading && !isError && !isEmpty && (
        <div className="space-y-6">
          {GROUP_KEYS.map((group) => {
            const items = grouped[group];
            if (items.length === 0) return null;
            const totalQty = items.reduce((sum, it) => sum + it.quantity, 0);
            return (
              <section key={group}>
                <h2 className="text-xs font-semibold text-text-tertiary mb-2 flex items-center gap-1.5">
                  {group}
                  <span className="text-[11px] font-normal text-text-tertiary">({totalQty}개 보유)</span>
                </h2>
                <div className="space-y-2">
                  {items.map((item) => (
                    <InventoryRow key={item.id} item={item} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
