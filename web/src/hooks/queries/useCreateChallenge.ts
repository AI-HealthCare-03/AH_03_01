import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createChallenge } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";

export function useCreateChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createChallenge,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHALLENGES_KEY] });
    },
  });
}
