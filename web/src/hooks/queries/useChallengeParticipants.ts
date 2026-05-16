import { useQuery } from "@tanstack/react-query";
import { fetchParticipants } from "@/lib/api/challenge";

export const PARTICIPANTS_KEY = "challenge-participants" as const;

export function useChallengeParticipants(challengeId: number | null) {
  return useQuery({
    queryKey: [PARTICIPANTS_KEY, challengeId],
    queryFn: () => fetchParticipants(challengeId!),
    enabled: !!challengeId,
  });
}
