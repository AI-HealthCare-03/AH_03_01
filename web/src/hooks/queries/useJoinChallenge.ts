import { useMutation, useQueryClient } from "@tanstack/react-query";
import { joinChallenge } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";
import { CHALLENGE_KEY } from "./useChallenge";
import { PARTICIPANTS_KEY } from "./useChallengeParticipants";
import { MY_ACTIVE_CHALLENGES_KEY } from "./useMyActiveChallenges";

export function useJoinChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      challengeId,
      inviteCode,
    }: {
      challengeId: number;
      inviteCode?: string;
    }) => joinChallenge(challengeId, inviteCode),
    onSuccess: (_, { challengeId }) => {
      qc.invalidateQueries({ queryKey: [CHALLENGES_KEY] });
      qc.invalidateQueries({ queryKey: [CHALLENGE_KEY, challengeId] });
      qc.invalidateQueries({ queryKey: [PARTICIPANTS_KEY, challengeId] });
      qc.invalidateQueries({ queryKey: MY_ACTIVE_CHALLENGES_KEY });
    },
  });
}
