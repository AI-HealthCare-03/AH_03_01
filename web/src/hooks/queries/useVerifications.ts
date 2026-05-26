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
    refetchInterval: (query) => {
      const data = query.state.data as VerificationListResponse | undefined;
      const hasPending = (data?.items ?? []).some((v) => v.status === "PENDING");
      return hasPending ? 5000 : false;
    },
    refetchIntervalInBackground: false,
  });
}
