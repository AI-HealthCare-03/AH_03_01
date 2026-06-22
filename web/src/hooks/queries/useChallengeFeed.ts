import { useQuery } from "@tanstack/react-query";
import { fetchChallengeFeed } from "@/lib/api/challenge";
import type { VerificationFeedResponse } from "@/types/challenge";

export const CHALLENGE_FEED_KEY = "challenge-feed";

export function useChallengeFeed(challengeId: number) {
  return useQuery<VerificationFeedResponse>({
    queryKey: [CHALLENGE_FEED_KEY, challengeId],
    queryFn: () => fetchChallengeFeed(challengeId),
    enabled: !!challengeId,
  });
}
