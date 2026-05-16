import { useQuery } from "@tanstack/react-query";
import { fetchChallenge } from "@/lib/api/challenge";

export const CHALLENGE_KEY = "challenge" as const;

export function useChallenge(id: number | null) {
  return useQuery({
    queryKey: [CHALLENGE_KEY, id],
    queryFn: () => fetchChallenge(id!),
    enabled: !!id,
  });
}
