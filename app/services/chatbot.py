from __future__ import annotations

import logging
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

_logger = logging.getLogger(__name__)

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

        if mode == "faq":
            # FAQ 모드는 LLM 호출이 없어 트랜잭션 안에서 완결.
            async with in_transaction():
                session = await self._resolve_session(user, data)
                await self.message_repo.create(
                    data={
                        "session_id": session.id,
                        "role": ChatMessageRole.USER,
                        "message_type": ChatMessageType.TEXT,
                        "content": data.message,
                    }
                )
                bot_message = await self._answer_with_faq(session, data)
                await self.session_repo.touch(session, message_increment=2)
            return self._build_response(session.id, bot_message)

        # RAG 모드: ChatRAGGraph(OpenAI 외부 호출) 는 트랜잭션 바깥에서 수행해
        # DB 커넥션 점유 시간을 최소화한다 (API 계약 §9 트랜잭션 정책).
        async with in_transaction():
            session = await self._resolve_session(user, data)
            await self.message_repo.create(
                data={
                    "session_id": session.id,
                    "role": ChatMessageRole.USER,
                    "message_type": ChatMessageType.TEXT,
                    "content": data.message,
                }
            )

        # ChatRAGGraph 내부 예외는 run_chat_rag 의 try/except 가 fallback 으로 흡수하지만,
        # 그래프 진입 전(예: import 단계) 또는 SDK 가 예외를 raise 하는 케이스를 위해
        # 한 단계 더 방어. 어떤 경우에도 사용자 메시지만 남는 고아 세션이 생기지 않도록
        # SYSTEM placeholder 응답을 보장한다.
        try:
            rag_result = await self.rag.answer(
                query=data.message,
                user_id=user.id,
                thread_id=str(session.id),
            )
        except Exception as e:  # noqa: BLE001 — 모든 예외를 SYSTEM placeholder 로 흡수
            _logger.error("rag.answer 실패, SYSTEM placeholder 저장: %s", type(e).__name__)
            from app.graphs.chat_rag_graph import FALLBACK_MEDICAL, MEDICAL_DISCLAIMER
            from app.services.ml.chatbot_rag import RAGAnswer

            rag_result = RAGAnswer(
                answer=FALLBACK_MEDICAL,
                confidence=0.0,
                model_version="chatragraph-v1",
                fallback=True,
                disclaimer=MEDICAL_DISCLAIMER,
            )

        async with in_transaction():
            bot_message = await self._persist_rag_message(session, rag_result)
            await self.session_repo.touch(session, message_increment=2)

        return self._build_response(session.id, bot_message)

    @staticmethod
    def _build_response(conversation_id: int, bot_message: ChatbotMessage) -> dict[str, Any]:
        extra = bot_message.extra_data or {}
        return {
            "conversation_id": conversation_id,
            "message_id": bot_message.id,
            "role": bot_message.role,
            "message_type": bot_message.message_type,
            "answer": bot_message.content,
            "sources": bot_message.sources,
            "confidence": bot_message.confidence,
            "model_version": bot_message.model_version,
            # 신규 7필드 — extra_data 가 없으면(faq 모드 등) 기본값으로 채워져 역호환성 유지
            "disclaimer": extra.get("disclaimer", "본 답변은 의학적 진단을 대체하지 않습니다."),
            "intent": extra.get("intent"),
            "needs_health_data": bool(extra.get("needs_health_data", False)),
            "missing_fields": list(extra.get("missing_fields") or []),
            "action_hint": extra.get("action_hint"),
            "is_fallback": bool(extra.get("is_fallback", False)),
            "eval_revision_count": extra.get("eval_revision_count"),
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

    async def _persist_rag_message(self, session: ChatbotSession, rag_result: RAGAnswer) -> ChatbotMessage:
        """ChatRAGGraph 결과를 ChatbotMessage 로 저장.

        message_type 분기 (API 계약 §6 매핑):
        - needs_health_data=true  → SYSTEM (개인화 건강 정보 안내)
        - is_fallback=true        → SYSTEM (Evaluator 한도 초과 폴백)
        - 그 외                   → RAG
        """
        if rag_result.needs_health_data or rag_result.fallback:
            message_type = ChatMessageType.SYSTEM
        else:
            message_type = ChatMessageType.RAG

        extra_data = {
            "intent": rag_result.intent,
            "needs_health_data": rag_result.needs_health_data,
            "missing_fields": list(rag_result.missing_fields),
            "action_hint": rag_result.action_hint,
            "is_fallback": rag_result.fallback,
            "eval_revision_count": rag_result.eval_revision_count,
            "disclaimer": rag_result.disclaimer,
        }

        return await self.message_repo.create(
            data={
                "session_id": session.id,
                "role": ChatMessageRole.BOT,
                "message_type": message_type,
                "content": rag_result.answer,
                "sources": [s.to_dict() for s in rag_result.sources],
                "confidence": rag_result.confidence,
                "model_version": rag_result.model_version,
                "extra_data": extra_data,
            }
        )
