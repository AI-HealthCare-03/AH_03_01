import { useQuery } from "@tanstack/react-query";
import { fetchVerifications } from "@/lib/api/challenge";
import type { VerificationListResponse } from "@/types/challenge";

export const VERIFICATIONS_KEY = "challenge-verifications" as const;

/**
 * 챌린지의 인증 목록 조회. PENDING 상태가 1건 이상이면 ai_worker 의 SigLIP2
 * 판정 결과를 받기 위해 5초마다 자동 refetch. 모든 결과가 확정되면 폴링 중단.
 */
export function useVerifications(challengeId: number | null) {
  return useQuery({
    queryKey: [VERIFICATIONS_KEY, challengeId],
    queryFn: () => fetchVerifications(challengeId!),
    enabled: !!challengeId,
    /* 인증 페이지에서 인증 후 상세로 돌아왔을 때 "오늘 인증 완료" 가 즉시 반영돼야 한다.
       전역 기본값(refetchOnMount: false, staleTime 60s)은 인증 페이지에서 발생한
       invalidate 를 unmount 상태였던 이 쿼리에 적용하지 못해, 복귀 시 stale 캐시를
       그대로 보여준다. 마운트마다 항상 재요청하도록 오버라이드한다. */
    refetchOnMount: "always",
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data as VerificationListResponse | undefined;
      const hasPending = (data?.items ?? []).some((v) => v.status === "PENDING");
      return hasPending ? 5000 : false;
    },
    refetchIntervalInBackground: false,
  });
}
