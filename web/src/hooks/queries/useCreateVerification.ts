import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createVerification } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";
import { VERIFICATIONS_KEY } from "./useVerifications";
import type { CreateVerificationRequest, VerificationMethod } from "@/types/challenge";

export function useCreateVerification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      body,
      method,
    }: {
      body: CreateVerificationRequest;
      method: VerificationMethod;
    }) => createVerification(body, method),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: [CHALLENGES_KEY] });
      qc.invalidateQueries({ queryKey: [VERIFICATIONS_KEY, data.challenge_id] });
    },
  });
}
