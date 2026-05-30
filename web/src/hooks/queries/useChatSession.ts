import { useQuery } from "@tanstack/react-query";
import { fetchChatSession } from "@/lib/api/chat";

export const CHAT_SESSION_KEY = "chat-session";

export function useChatSession(sessionId: number | undefined) {
  return useQuery({
    queryKey: [CHAT_SESSION_KEY, sessionId],
    queryFn: () => fetchChatSession(sessionId!),
    enabled: !!sessionId,
  });
}
