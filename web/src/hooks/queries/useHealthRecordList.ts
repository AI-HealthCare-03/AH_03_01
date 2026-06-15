import { useQuery } from "@tanstack/react-query";
import { fetchHealthRecordList } from "@/lib/api/health";

export const HEALTH_RECORD_LIST_KEY = "health-record-list";

export function useHealthRecordList(
  params: {
    recordType?: string;
    subType?: string;
    from?: string;
    to?: string;
    page?: number;
    size?: number;
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [HEALTH_RECORD_LIST_KEY, params],
    queryFn: () => fetchHealthRecordList(params),
    enabled: options?.enabled ?? true,
  });
}
