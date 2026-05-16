import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createHealthRecord } from "@/lib/api/health";
import { HEALTH_RECORD_LIST_KEY } from "./useHealthRecordList";
import { HEALTH_STATISTICS_KEY } from "./useHealthStatistics";

export function useCreateHealthRecord() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createHealthRecord,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [HEALTH_RECORD_LIST_KEY] });
      queryClient.invalidateQueries({ queryKey: [HEALTH_STATISTICS_KEY] });
    },
  });
}
