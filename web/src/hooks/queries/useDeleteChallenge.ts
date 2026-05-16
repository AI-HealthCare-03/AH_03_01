import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteChallenge } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";

export function useDeleteChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteChallenge,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHALLENGES_KEY] });
    },
  });
}
