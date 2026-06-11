"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { notifHistoryKey } from "@/lib/notifKeys";

/* ─────────────────────────────────────────────────────
   알림 드롭다운 컴포넌트
   알림 내역은 localStorage("notification-history:{userId}") 에 유저별 저장
───────────────────────────────────────────────────── */

/** @deprecated 직접 사용하지 말고 notifHistoryKey() 를 사용하세요 */
export const NOTIF_HISTORY_KEY = "notification-history";

export type NotifCategory = "복약" | "챌린지" | "커뮤니티" | "위험도";

export interface NotifItem {
  id: string;
  category: NotifCategory;
  title: string;
  body: string;
  timestamp: number; // Date.now()
  read: boolean;
  checked?: boolean; // 복약 완료 여부 (복약 카테고리 전용)
}

const CATEGORIES: Array<"전체" | NotifCategory> = ["전체", "복약", "챌린지", "커뮤니티", "위험도"];

/* ── 알림 저장 유틸 (외부에서도 사용 가능) ──────────── */
export function pushNotification(item: Omit<NotifItem, "id" | "timestamp" | "read">, ts?: number) {
  try {
    const raw = localStorage.getItem(notifHistoryKey());
    const list: NotifItem[] = raw ? JSON.parse(raw) : [];
    const next: NotifItem = {
      ...item,
      id: Math.random().toString(36).slice(2, 10),
      timestamp: ts ?? Date.now(),
      read: false,
    };
    // 최대 100개 유지
    localStorage.setItem(notifHistoryKey(), JSON.stringify([next, ...list].slice(0, 100)));
    // 드롭다운에 갱신 신호 전송
    window.dispatchEvent(new CustomEvent("notif-updated"));
  } catch { /* 무시 */ }
}

function loadNotifications(): NotifItem[] {
  try {
    const raw = localStorage.getItem(notifHistoryKey());
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function formatTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "방금";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}시간 전`;
  return new Date(ts).toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

const CATEGORY_COLOR: Record<NotifCategory, string> = {
  복약: "bg-blue-100 text-blue-700",
  챌린지: "bg-yellow-100 text-yellow-700",
  커뮤니티: "bg-green-100 text-green-700",
  위험도: "bg-red-100 text-red-700",
};

/* ── 메인 컴포넌트 ──────────────────────────────────── */
export default function NotificationDropdown() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"전체" | NotifCategory>("전체");
  const [list, setList] = useState<NotifItem[]>([]);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  // 마운트 시 초기 로드 + notif-updated 이벤트로 자동 갱신
  useEffect(() => {
    setList(loadNotifications());
    const handler = () => setList(loadNotifications());
    window.addEventListener("notif-updated", handler);
    return () => window.removeEventListener("notif-updated", handler);
  }, []);

  // 드롭다운 열릴 때도 최신 내역 로드
  useEffect(() => {
    if (open) setList(loadNotifications());
  }, [open]);

  // 외부 클릭 시 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // 읽지 않은 알림 수
  const unread = list.filter((n) => !n.read).length;

  // 탭별 필터
  const filtered = tab === "전체" ? list : list.filter((n) => n.category === tab);

  // 전체 읽음 처리
  const markAllRead = () => {
    const next = list.map((n) => ({ ...n, read: true }));
    setList(next);
    try { localStorage.setItem(notifHistoryKey(), JSON.stringify(next)); } catch { /* 무시 */ }
  };

  // 복약 완료 체크 토글
  const toggleMedCheck = (id: string) => {
    const next = list.map((n) => n.id === id ? { ...n, checked: !n.checked, read: true } : n);
    setList(next);
    try { localStorage.setItem(notifHistoryKey(), JSON.stringify(next)); } catch { /* 무시 */ }
  };

  return (
    <div ref={wrapRef} className="relative">
      {/* 종 버튼 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative flex items-center justify-center w-9 h-9 rounded-full hover:bg-surface transition-colors"
        aria-label="알림"
      >
        <Bell size={20} strokeWidth={1.8} className="text-text-secondary" />
        {/* 배지 */}
        {unread > 0 && (
          <span className="absolute bottom-0.5 right-0.5 min-w-[16px] h-4 px-1 flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full leading-none">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {/* 드롭다운 */}
      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-border rounded-[16px] shadow-lg z-50 overflow-hidden">
          {/* 헤더 */}
          <div className="flex items-center justify-between px-4 pt-4 pb-2">
            <p className="text-sm font-bold text-text-primary">알림</p>
            {unread > 0 && (
              <button
                type="button"
                onClick={markAllRead}
                className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
              >
                모두 읽음
              </button>
            )}
          </div>

          {/* 카테고리 탭 */}
          <div className="flex gap-1 px-4 pb-2 overflow-x-auto scrollbar-hide">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setTab(c)}
                className={[
                  "shrink-0 px-2.5 py-1 text-xs font-semibold rounded-full border transition-colors",
                  tab === c
                    ? "bg-brand-black text-white border-brand-black"
                    : "bg-white text-text-secondary border-border hover:border-text-primary",
                ].join(" ")}
              >
                {c}
              </button>
            ))}
          </div>

          {/* 알림 목록 */}
          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {filtered.length === 0 ? (
              <p className="py-8 text-center text-sm text-text-tertiary">알림이 없어요</p>
            ) : (
              filtered.map((n) => (
                <div
                  key={n.id}
                  className={["px-4 py-3 min-h-[76px] transition-colors", n.read ? "bg-white" : "bg-surface"].join(" ")}
                >
                  <div className="flex justify-between gap-2 h-full">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${CATEGORY_COLOR[n.category]}`}>
                          {n.category}
                        </span>
                        {!n.read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-sm font-semibold text-text-primary leading-snug">{n.title}</p>
                      <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{n.body}</p>
                    </div>
                    <div className="flex flex-col items-end justify-between shrink-0 min-h-[52px]">
                      <span className="text-[10px] text-text-tertiary">
                        {formatTime(n.timestamp)}
                      </span>
                      {n.category === "복약" && (
                        <button
                          type="button"
                          onClick={() => toggleMedCheck(n.id)}
                          className={[
                            "px-2.5 py-1 text-xs rounded-full border transition-colors",
                            n.checked
                              ? "bg-green-100 border-green-400 text-green-700 font-medium"
                              : "bg-white border-border text-text-secondary hover:border-text-primary",
                          ].join(" ")}
                        >
                          {n.checked ? "✓ 복약 완료" : "○ 복약 완료"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
