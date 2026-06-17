"use client";

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { updateNotifChecked } from "@/lib/notifKeys";
import { useToast } from "@/components/ui/Toast";

export const MED_BANNER_EVENT = "med-banner-show";

const ENTER_MS = 300; // globals.css med-banner-in 애니메이션 duration과 일치

interface BannerItem {
  notifId: string;
  title: string;
  body: string;
  leaving: boolean;
}

export default function MedicationBanner() {
  const [queue, setQueue] = useState<BannerItem[]>([]);
  const dismissTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const enteredAtMap = useRef<Map<string, number>>(new Map());
  const { showToast } = useToast();

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as Record<string, unknown>;
      const { notifId, title, body } = detail ?? {};
      if (typeof notifId !== "string" || !notifId || typeof title !== "string") return;
      enteredAtMap.current.set(notifId, Date.now());
      setQueue((prev) => [
        ...prev,
        { notifId, title, body: typeof body === "string" ? body : "", leaving: false },
      ]);
    };
    window.addEventListener(MED_BANNER_EVENT, handler);
    return () => window.removeEventListener(MED_BANNER_EVENT, handler);
  }, []);

  // unmount 시 진행 중인 dismiss 타이머 및 enteredAt 기록 전부 정리
  useEffect(() => {
    return () => {
      dismissTimers.current.forEach(clearTimeout);
      dismissTimers.current.clear();
      enteredAtMap.current.clear();
    };
  }, []);

  const dismiss = (notifId: string) => {
    if (dismissTimers.current.has(notifId)) return;

    const startLeave = () => {
      setQueue((prev) =>
        prev.map((b) => (b.notifId === notifId ? { ...b, leaving: true } : b))
      );
      const removeTid = setTimeout(() => {
        setQueue((prev) => prev.filter((b) => b.notifId !== notifId));
        dismissTimers.current.delete(notifId);
        enteredAtMap.current.delete(notifId);
      }, 280);
      dismissTimers.current.set(notifId, removeTid);
    };

    // enter 애니메이션이 끝나기 전에 dismiss되면 완료 후 leave 시작 (position snap 방지)
    // queue 클로저가 아닌 ref에서 읽어 stale closure 문제를 방지한다.
    const enteredAt = enteredAtMap.current.get(notifId);
    const enterRemaining = enteredAt ? Math.max(0, ENTER_MS - (Date.now() - enteredAt)) : 0;

    if (enterRemaining > 0) {
      const tid = setTimeout(startLeave, enterRemaining);
      dismissTimers.current.set(notifId, tid);
    } else {
      startLeave();
    }
  };

  const markDone = (notifId: string) => {
    try {
      updateNotifChecked(notifId, true);
    } catch {
      showToast("복약 완료 저장에 실패했어요. 다시 시도해 주세요.", "error");
      return;
    }
    dismiss(notifId);
  };

  const current = queue[0];
  if (!current) return null;
  const activeCount = queue.filter((b) => !b.leaving).length;

  return (
    <div className="med-banner fixed top-0 left-0 right-0 z-[60] flex justify-center px-4 pt-3 pointer-events-none">
      <div
        className={[
          "pointer-events-auto w-full max-w-sm rounded-2xl overflow-hidden",
          "bg-white border border-blue-200 shadow-lg",
          current.leaving ? "med-banner-leave" : "med-banner-enter",
        ].join(" ")}
      >
        <div className="flex items-start gap-3 p-4">
          <span className="text-xl leading-none mt-0.5" aria-hidden>💊</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-text-primary leading-snug">{current.title}</p>
            <p className="text-xs text-text-secondary mt-0.5">{current.body}</p>
          </div>
          {activeCount > 1 && (
            <span className="shrink-0 text-[10px] text-text-tertiary font-medium self-start mt-0.5 mr-1">
              1 / {activeCount}
            </span>
          )}
          <button
            type="button"
            onClick={() => dismiss(current.notifId)}
            className="shrink-0 text-text-tertiary hover:text-text-primary transition-colors -mt-0.5"
            aria-label="배너 닫기"
          >
            <X size={16} />
          </button>
        </div>
        <div className="flex border-t border-gray-100">
          <button
            type="button"
            onClick={() => dismiss(current.notifId)}
            className="flex-1 py-2.5 text-xs text-text-secondary hover:bg-gray-50 transition-colors rounded-bl-2xl"
          >
            나중에
          </button>
          <div className="w-px bg-gray-100" />
          <button
            type="button"
            onClick={() => markDone(current.notifId)}
            className="flex-1 py-2.5 text-xs font-semibold text-blue-600 hover:bg-blue-50 transition-colors rounded-br-2xl"
          >
            복약 완료
          </button>
        </div>
      </div>
    </div>
  );
}
