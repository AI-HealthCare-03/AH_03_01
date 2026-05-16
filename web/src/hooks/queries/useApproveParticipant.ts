import { useMutation, useQueryClient } from "@tanstack/react-query";
import { approveParticipant } from "@/lib/api/challenge";
import { PARTICIPANTS_KEY } from "./useChallengeParticipants";

export function useApproveParticipant(challengeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      action,
    }: {
      userId: number;
      action: "approve" | "reject";
    }) => approveParticipant(challengeId, userId, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [PARTICIPANTS_KEY, challengeId] });
    },
  });
}
