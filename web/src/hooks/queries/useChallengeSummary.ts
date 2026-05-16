import { useQuery } from "@tanstack/react-query";
import { fetchChallengeSummary } from "@/lib/api/challenge";

export const CHALLENGE_SUMMARY_KEY = "challenge-summary" as const;

export function useChallengeSummary(period: "weekly" | "monthly") {
  return useQuery({
    queryKey: [CHALLENGE_SUMMARY_KEY, period],
    queryFn: () => fetchChallengeSummary(period),
  });
}
