import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toggleLike } from "@/lib/api/challenge";
import { CHALLENGE_FEED_KEY } from "./useChallengeFeed";

export function useToggleLike(challengeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (verificationId: number) => toggleLike(verificationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHALLENGE_FEED_KEY, challengeId] });
    },
  });
}
