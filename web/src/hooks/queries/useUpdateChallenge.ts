import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateChallenge } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";
import { CHALLENGE_KEY } from "./useChallenge";

export function useUpdateChallenge(challengeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof updateChallenge>[1]) =>
      updateChallenge(challengeId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHALLENGES_KEY] });
      qc.invalidateQueries({ queryKey: [CHALLENGE_KEY, challengeId] });
    },
  });
}
