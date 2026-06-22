import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createVerification } from "@/lib/api/challenge";
import { CHALLENGES_KEY } from "./useChallenges";
import { CHALLENGE_KEY } from "./useChallenge";
import { VERIFICATIONS_KEY } from "./useVerifications";
import { CHALLENGE_FEED_KEY } from "./useChallengeFeed";
import { PARTICIPANTS_KEY } from "./useChallengeParticipants";
import { POINT_BALANCE_KEY } from "./usePointBalance";
import { WEEKLY_XP_KEY } from "./useWeeklyXp";
import { MY_PET_QUERY_KEY } from "./useMyPet";
import { MY_ACTIVE_CHALLENGES_KEY } from "./useMyActiveChallenges";
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
      qc.invalidateQueries({ queryKey: [CHALLENGE_KEY, data.challenge_id] });
      qc.invalidateQueries({ queryKey: [VERIFICATIONS_KEY, data.challenge_id] });
      qc.invalidateQueries({ queryKey: [CHALLENGE_FEED_KEY, data.challenge_id] });
      qc.invalidateQueries({ queryKey: [PARTICIPANTS_KEY, data.challenge_id] });
      qc.invalidateQueries({ queryKey: ["challenge-feed-history", data.challenge_id] });
      /* APPROVED 인증 시 백엔드에서 포인트 잔액 / 주간 XP / 펫 XP / 내 진행 챌린지가
         함께 갱신된다 (app/services/challenge.py grant_daily + pet xp + experience).
         관련 캐시도 무효화해서 보상이 즉시 UI 에 반영되도록 한다. */
      qc.invalidateQueries({ queryKey: POINT_BALANCE_KEY });
      qc.invalidateQueries({ queryKey: WEEKLY_XP_KEY });
      qc.invalidateQueries({ queryKey: MY_PET_QUERY_KEY });
      qc.invalidateQueries({ queryKey: MY_ACTIVE_CHALLENGES_KEY });
    },
  });
}
