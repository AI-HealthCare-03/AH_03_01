import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createPrediction } from "@/lib/api/health";
import { LATEST_PREDICTIONS_KEY } from "./useLatestPredictions";

export function useCreatePrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPrediction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LATEST_PREDICTIONS_KEY });
    },
  });
}
