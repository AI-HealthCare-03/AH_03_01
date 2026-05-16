import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createReaction } from "@/lib/api/challenge";
import { REACTIONS_KEY } from "./useVerificationReactions";
import type { CreateReactionRequest } from "@/types/challenge";

export function useCreateReaction(verificationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateReactionRequest) =>
      createReaction(verificationId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [REACTIONS_KEY, verificationId] });
    },
  });
}
