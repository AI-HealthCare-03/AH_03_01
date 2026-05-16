import { useQuery } from "@tanstack/react-query";
import { fetchVerificationReactions } from "@/lib/api/challenge";

export const REACTIONS_KEY = "verification-reactions" as const;

export function useVerificationReactions(verificationId: number | null) {
  return useQuery({
    queryKey: [REACTIONS_KEY, verificationId],
    queryFn: () => fetchVerificationReactions(verificationId!),
    enabled: !!verificationId,
  });
}
