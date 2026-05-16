from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.dtos.chatbot import ChatMessageRequest
from app.models.chatbot import (
    ChatbotFaq,
    ChatbotMessage,
    ChatbotSession,
    ChatMessageRole,
    ChatMessageType,
    FaqCategory,
)
from app.models.users import User
from app.repositories.chatbot_repository import (
    ChatbotFaqRepository,
    ChatbotMessageRepository,
    ChatbotSessionRepository,
)
from app.services.ml import ChatbotRAG, RAGAnswer

MAX_TITLE_LENGTH = 30


class ChatbotFaqService:
    def __init__(self) -> None:
        self.repo = ChatbotFaqRepository()

    async def list(self, category: FaqCategory | None, keyword: str | None) -> list[ChatbotFaq]:
        return await self.repo.list_active(category, keyword)


class ChatbotConversationService:
    def __init__(self) -> None:
        self.faq_repo = ChatbotFaqRepository()
        self.session_repo = ChatbotSessionRepository()
        self.message_repo = ChatbotMessageRepository()
        self.rag = ChatbotRAG()

    async def list_sessions(self, user: User) -> list[ChatbotSession]:
        return await self.session_repo.list_for_user(user.id)

    async def get_session_messages(self, user: User, session_id: int) -> tuple[ChatbotSession, list[ChatbotMessage]]:
        session = await self.session_repo.get_owned(session_id, user.id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
        messages = await self.message_repo.list_for_session(session.id)
        return session, messages

    async def handle_message(self, user: User, mode: str, data: ChatMessageRequest) -> dict[str, Any]:
        if mode not in {"faq", "rag"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode 는 faq|rag 입니다.")

        async with in_transaction():
            session = await self._resolve_session(user, data)

            # 사용자 메시지 기록
            await self.message_repo.create(
                data={
                    "session_id": session.id,
                    "role": ChatMessageRole.USER,
                    "message_type": ChatMessageType.TEXT,
                    "content": data.message,
                }
            )

            if mode == "faq":
                bot_message = await self._answer_with_faq(session, data)
            else:
                bot_message = await self._answer_with_rag(session, data)

            await self.session_repo.touch(session, message_increment=2)

        return {
            "conversation_id": session.id,
            "message_id": bot_message.id,
            "role": bot_message.role,
            "message_type": bot_message.message_type,
            "answer": bot_message.content,
            "sources": bot_message.sources,
            "confidence": bot_message.confidence,
            "model_version": bot_message.model_version,
        }

    async def _resolve_session(self, user: User, data: ChatMessageRequest) -> ChatbotSession:
        if data.conversation_id is not None:
            session = await self.session_repo.get_owned(data.conversation_id, user.id)
            if session is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
            return session
        # 새 세션: 첫 메시지로 타이틀 생성
        title = data.message[:MAX_TITLE_LENGTH]
        return await self.session_repo.create(user.id, title=title)

    async def _answer_with_faq(self, session: ChatbotSession, data: ChatMessageRequest) -> ChatbotMessage:
        faq: ChatbotFaq | None = None
        if data.faq_id is not None:
            faq = await self.faq_repo.get(data.faq_id)
        else:
            # 키워드 매칭 폴백: 메시지가 question 에 포함되는 FAQ 검색
            candidates = await self.faq_repo.list_active(keyword=data.message)
            faq = candidates[0] if candidates else None

        if faq is None:
            return await self.message_repo.create(
                data={
                    "session_id": session.id,
                    "role": ChatMessageRole.BOT,
                    "message_type": ChatMessageType.SYSTEM,
                    "content": "일치하는 FAQ 가 없어요. 다른 질문으로 시도해 주세요.",
                    "faq_id": None,
                    "sources": [],
                    "confidence": 0.0,
                }
            )

        return await self.message_repo.create(
            data={
                "session_id": session.id,
                "role": ChatMessageRole.BOT,
                "message_type": ChatMessageType.FAQ,
                "content": faq.answer,
                "faq_id": faq.id,
                "sources": [],
                "confidence": 1.0,
            }
        )

    async def _answer_with_rag(self, session: ChatbotSession, data: ChatMessageRequest) -> ChatbotMessage:
        rag_result: RAGAnswer = await self.rag.answer(query=data.message)
        return await self.message_repo.create(
            data={
                "session_id": session.id,
                "role": ChatMessageRole.BOT,
                "message_type": ChatMessageType.RAG,
                "content": rag_result.answer,
                "sources": [s.to_dict() for s in rag_result.sources],
                "confidence": rag_result.confidence,
                "model_version": rag_result.model_version,
            }
        )
