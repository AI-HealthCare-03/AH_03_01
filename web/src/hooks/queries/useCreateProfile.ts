import { useMutation, useQueryClient } from "@tanstack/react-query";
import { upsertHealthProfile } from "@/lib/api/health";
import { HEALTH_PROFILE_KEY } from "./useHealthProfile";
import { PROFILE_COMPLETENESS_KEY } from "./useProfileCompleteness";

export function useCreateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: upsertHealthProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HEALTH_PROFILE_KEY });
      queryClient.invalidateQueries({ queryKey: PROFILE_COMPLETENESS_KEY });
    },
  });
}
