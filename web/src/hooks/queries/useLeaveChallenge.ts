import { useMutation, useQueryClient } from "@tanstack/react-query";
import { leaveChallenge } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";

export function useLeaveChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: leaveChallenge,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHALLENGES_KEY] });
    },
  });
}
