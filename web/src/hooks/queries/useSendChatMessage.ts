import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sendChatMessage } from "@/lib/api/chat";
import { CHAT_SESSIONS_KEY } from "./useChatSessions";
import { CHAT_SESSION_KEY } from "./useChatSession";

export function useSendChatMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      body,
      mode,
    }: {
      body: Parameters<typeof sendChatMessage>[0];
      mode?: "rag" | "faq";
    }) => sendChatMessage(body, mode),
    onSuccess: (data) => {
      /* 세션 목록 갱신 */
      queryClient.invalidateQueries({ queryKey: [CHAT_SESSIONS_KEY] });
      /* 해당 세션 상세 갱신 */
      queryClient.invalidateQueries({
        queryKey: [CHAT_SESSION_KEY, data.conversation_id],
      });
    },
  });
}
