import { useQuery } from "@tanstack/react-query";
import { fetchVerificationReactions } from "@/lib/api/challenge";
import type { ReactionListResponse } from "@/types/challenge";

export const COMMENTS_KEY = "verification-comments";

export function useVerificationComments(verificationId: number | null) {
  return useQuery<ReactionListResponse>({
    queryKey: [COMMENTS_KEY, verificationId],
    queryFn: () => fetchVerificationReactions(verificationId!),
    enabled: !!verificationId,
  });
}
