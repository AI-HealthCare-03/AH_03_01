import { useQuery } from "@tanstack/react-query";
import { fetchChatSessions } from "@/lib/api/chat";

export const CHAT_SESSIONS_KEY = "chat-sessions";

export function useChatSessions() {
  return useQuery({
    queryKey: [CHAT_SESSIONS_KEY],
    queryFn: fetchChatSessions,
  });
}
