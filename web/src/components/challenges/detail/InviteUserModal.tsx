"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import {
  inviteUserToChallenge,
  searchUsersByNickname,
  type UserSearchItem,
} from "@/lib/api/challenge";
import { extractErrorMessage } from "@/lib/api/client";

/* =========================================
   닉네임 검색 → 사용자 초대 모달
   ========================================= */

interface InviteUserModalProps {
  challengeId: number;
  open: boolean;
  onClose: () => void;
  /** 이미 참여 중인 user_id 집합 (검색 결과에서 회색 처리) */
  excludeUserIds?: number[];
}

export default function InviteUserModal({
  challengeId,
  open,
  onClose,
  excludeUserIds = [],
}: InviteUserModalProps) {
  const { showToast } = useToast();
  const [keyword, setKeyword] = useState("");
  const [results, setResults] = useState<UserSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [invitedIds, setInvitedIds] = useState<Set<number>>(new Set());
  const inputRef = useRef<HTMLInputElement | null>(null);

  /* 모달 열릴 때 입력 포커스 + 상태 리셋 */
  useEffect(() => {
    if (open) {
      setKeyword("");
      setResults([]);
      setInvitedIds(new Set());
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  /* 키워드 변경 시 300ms debounce 검색 */
  useEffect(() => {
    if (!open) return;
    const q = keyword.trim();
    if (q.length === 0) {
      setResults([]);
      return;
    }
    setSearching(true);
    const handle = setTimeout(async () => {
      try {
        const items = await searchUsersByNickname(q);
        setResults(items);
      } catch (err) {
        showToast(extractErrorMessage(err), "error");
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [keyword, open, showToast]);

  /* ESC 로 닫기 */
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [open, onClose]);

  const inviteMutation = useMutation({
    mutationFn: (userId: number) => inviteUserToChallenge(challengeId, userId),
    onSuccess: (_, userId) => {
      setInvitedIds((prev) => new Set(prev).add(userId));
      showToast("초대를 보냈어요", "success");
    },
    onError: (err) => {
      showToast(extractErrorMessage(err), "error");
    },
  });

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="친구 초대"
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md bg-white rounded-[16px] shadow-xl overflow-hidden">
        {/* 헤더 */}
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-base font-bold text-text-primary">친구 초대</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="text-text-tertiary hover:text-text-primary"
          >
            ✕
          </button>
        </div>

        {/* 검색 */}
        <div className="px-5 py-4">
          <label
            htmlFor="invite-search"
            className="text-xs font-semibold text-text-secondary mb-2 block"
          >
            닉네임으로 친구 찾기
          </label>
          <input
            id="invite-search"
            ref={inputRef}
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="닉네임 일부를 입력하세요"
            className="w-full px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
            autoComplete="off"
          />

          {/* 결과 */}
          <div className="mt-3 max-h-72 overflow-y-auto">
            {keyword.trim() === "" ? (
              <p className="text-xs text-text-tertiary py-6 text-center">
                닉네임을 입력해 친구를 찾아 보세요
              </p>
            ) : searching ? (
              <p className="text-xs text-text-tertiary py-6 text-center">
                찾는 중…
              </p>
            ) : results.length === 0 ? (
              <p className="text-xs text-text-tertiary py-6 text-center">
                일치하는 사용자가 없어요
              </p>
            ) : (
              <ul className="space-y-2">
                {results.map((u) => {
                  const already = excludeUserIds.includes(u.id);
                  const invited = invitedIds.has(u.id);
                  return (
                    <li
                      key={u.id}
                      className="flex items-center justify-between gap-2 px-3 py-2 rounded-[10px] border border-border"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-8 h-8 rounded-full bg-brand flex items-center justify-center text-xs font-bold shrink-0">
                          {u.name[0]?.toUpperCase() ?? "U"}
                        </div>
                        <span className="text-sm font-medium text-text-primary truncate">
                          {u.name}
                        </span>
                      </div>
                      {already ? (
                        <span className="text-[11px] font-semibold text-text-tertiary px-2 py-1">
                          이미 참여 중
                        </span>
                      ) : invited ? (
                        <span className="text-[11px] font-semibold text-status-success px-2 py-1">
                          초대 완료
                        </span>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          loading={
                            inviteMutation.isPending &&
                            inviteMutation.variables === u.id
                          }
                          onClick={() => inviteMutation.mutate(u.id)}
                        >
                          초대
                        </Button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        {/* 푸터 안내 */}
        <div className="px-5 py-3 border-t border-border bg-surface">
          <p className="text-[11px] text-text-tertiary leading-snug">
            초대를 받으면 알림으로 안내돼요. 초대된 친구가 수락하면 멤버
            슬롯이 채워집니다.
          </p>
        </div>
      </div>
    </div>
  );
}
