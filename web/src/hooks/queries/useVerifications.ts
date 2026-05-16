import { useQuery } from "@tanstack/react-query";
import { fetchVerifications } from "@/lib/api/challenge";

export const VERIFICATIONS_KEY = "challenge-verifications" as const;

export function useVerifications(challengeId: number | null) {
  return useQuery({
    queryKey: [VERIFICATIONS_KEY, challengeId],
    queryFn: () => fetchVerifications(challengeId!),
    enabled: !!challengeId,
  });
}
