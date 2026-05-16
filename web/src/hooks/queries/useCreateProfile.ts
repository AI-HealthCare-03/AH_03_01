import { useMutation, useQueryClient } from "@tanstack/react-query";
import { upsertHealthProfile } from "@/lib/api/health";
import { HEALTH_PROFILE_KEY } from "./useHealthProfile";

export function useCreateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: upsertHealthProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HEALTH_PROFILE_KEY });
    },
  });
}
