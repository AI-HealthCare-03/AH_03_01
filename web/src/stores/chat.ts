import { create } from "zustand";
import type { ChatDisplayMessage } from "@/types/chat";

/* =========================================
   챗봇 위젯 Zustand 스토어
   - 위젯 열림/닫힘
   - 현재 conversation_id (같은 세션 이어붙임)
   - 표시 메시지 목록 (낙관적 업데이트 포함)
   - 뷰 전환 (chat | sessions)
   ========================================= */

export type ChatView = "chat" | "sessions";

interface ChatStore {
  isOpen: boolean;
  view: ChatView;
  conversationId: number | null;
  messages: ChatDisplayMessage[];

  /* 액션 */
  openChat: () => void;
  closeChat: () => void;
  toggleChat: () => void;
  setView: (view: ChatView) => void;
  setConversationId: (id: number) => void;
  addMessage: (msg: ChatDisplayMessage) => void;
  setMessages: (msgs: ChatDisplayMessage[]) => void;
  startNewConversation: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  isOpen: false,
  view: "chat",
  conversationId: null,
  messages: [],

  openChat: () => set({ isOpen: true }),
  closeChat: () => set({ isOpen: false }),
  toggleChat: () => set((s) => ({ isOpen: !s.isOpen })),

  setView: (view) => set({ view }),

  setConversationId: (id) => set({ conversationId: id }),

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  setMessages: (msgs) => set({ messages: msgs }),

  startNewConversation: () =>
    set({ conversationId: null, messages: [], view: "chat" }),
}));
