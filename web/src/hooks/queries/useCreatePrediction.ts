import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createPrediction } from "@/lib/api/health";
import { LATEST_PREDICTIONS_KEY } from "./useLatestPredictions";
import { PREDICTIONS_LIST_KEY } from "./usePredictionsList";
import { PROFILE_COMPLETENESS_KEY } from "./useProfileCompleteness";

export function useCreatePrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPrediction,
    onSuccess: () => {
      // 최신 예측 + 상세 예측 목록 모두 갱신 (위험인자 기여도 반영)
      queryClient.invalidateQueries({ queryKey: LATEST_PREDICTIONS_KEY });
      queryClient.invalidateQueries({ queryKey: [PREDICTIONS_LIST_KEY] });
      queryClient.invalidateQueries({ queryKey: PROFILE_COMPLETENESS_KEY });
    },
  });
}
