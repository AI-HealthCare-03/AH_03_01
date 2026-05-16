import { useQuery } from "@tanstack/react-query";
import { fetchPredictionsList } from "@/lib/api/health";
import type { DiseaseType } from "@/types/api";

export const PREDICTIONS_LIST_KEY = "predictions-list";

export function usePredictionsList(params?: {
  latest?: boolean;
  diseaseType?: DiseaseType;
}) {
  return useQuery({
    queryKey: [PREDICTIONS_LIST_KEY, params],
    queryFn: () => fetchPredictionsList(params),
  });
}
