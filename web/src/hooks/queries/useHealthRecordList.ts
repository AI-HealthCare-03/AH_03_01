import { useQuery } from "@tanstack/react-query";
import { fetchHealthRecordList } from "@/lib/api/health";

export const HEALTH_RECORD_LIST_KEY = "health-record-list";

export function useHealthRecordList(params: {
  recordType?: string;
  subType?: string;
  page?: number;
  size?: number;
}) {
  return useQuery({
    queryKey: [HEALTH_RECORD_LIST_KEY, params],
    queryFn: () => fetchHealthRecordList(params),
  });
}
