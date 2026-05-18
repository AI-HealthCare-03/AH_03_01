"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchMyInvitations, respondToInvitation, type MyInvitationItem } from "@/lib/api/challenge";
import { extractErrorMessage } from "@/lib/api/client";

/* =========================================
   받은 초대함 — /mypage/invitations
   친구가 보낸 챌린지 초대를 수락/거절
   ========================================= */

const MY_INVITATIONS_KEY = ["my-invitations"] as const;

export default function MyInvitationsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const { data, isLoading } = useQuery({
    queryKey: [...MY_INVITATIONS_KEY, "PENDING"],
    queryFn: () => fetchMyInvitations("PENDING"),
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    staleTime: 0,
  });

  const items: MyInvitationItem[] = data ?? [];

  const mutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "accept" | "reject" }) =>
      respondToInvitation(id, action),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: MY_INVITATIONS_KEY });
      showToast(vars.action === "accept" ? "참가했어요!" : "거절했어요", "success");
    },
    onError: (err) => showToast(extractErrorMessage(err), "error"),
  });

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div>
        <Link
          href="/mypage"
          className="text-sm text-text-tertiary hover:text-text-secondary inline-block mb-3"
        >
          ← 마이페이지
        </Link>
        <h1 className="text-xl font-black text-text-primary">받은 초대</h1>
        <p className="text-sm text-text-secondary mt-1">
          친구가 보낸 챌린지 초대를 확인하고 수락하면 바로 참가돼요
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-24 bg-surface animate-pulse rounded-[12px]" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white border border-dashed border-border rounded-[16px] py-12 text-center">
          <p className="text-3xl mb-2" aria-hidden="true">📨</p>
          <p className="text-sm text-text-secondary">받은 초대가 없어요</p>
          <p className="text-xs text-text-tertiary mt-1">
            친구가 챌린지에 초대하면 여기에 표시됩니다
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((inv) => (
            <li
              key={inv.id}
              className="bg-white border border-border rounded-[14px] px-4 py-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-text-tertiary mb-1">
                    {inv.inviter_name ?? "익명"} 님의 초대
                  </p>
                  <button
                    type="button"
                    onClick={() => router.push(`/challenges/${inv.challenge_id}`)}
                    className="text-sm font-bold text-text-primary text-left hover:underline truncate block w-full"
                  >
                    {inv.challenge_title ?? "이름 없는 챌린지"}
                  </button>
                  {inv.expires_at && (
                    <p className="text-[11px] text-text-tertiary mt-1">
                      만료 {new Date(inv.expires_at).toLocaleString("ko-KR", {
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  )}
                </div>
              </div>
              <div className="mt-3 flex gap-2 justify-end">
                <Button
                  variant="secondary"
                  size="sm"
                  loading={
                    mutation.isPending &&
                    mutation.variables?.id === inv.id &&
                    mutation.variables?.action === "reject"
                  }
                  onClick={() => mutation.mutate({ id: inv.id, action: "reject" })}
                >
                  거절
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  loading={
                    mutation.isPending &&
                    mutation.variables?.id === inv.id &&
                    mutation.variables?.action === "accept"
                  }
                  onClick={() => mutation.mutate({ id: inv.id, action: "accept" })}
                >
                  수락
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
