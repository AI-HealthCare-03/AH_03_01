from typing import Any

from tortoise.expressions import Q

from app.models.chatbot import (
    ChatbotFaq,
    ChatbotMessage,
    ChatbotSession,
    FaqCategory,
)


class ChatbotFaqRepository:
    def __init__(self) -> None:
        self._model = ChatbotFaq

    async def list_active(
        self,
        category: FaqCategory | None = None,
        keyword: str | None = None,
    ) -> list[ChatbotFaq]:
        qs = self._model.filter(is_active=True)
        if category is not None:
            qs = qs.filter(category=category)
        if keyword:
            # 사용자 발화는 보통 question 의 부분 문자열이 아니라 단어를 공유.
            # 2글자 이상 토큰을 추출해 OR 매칭. 토큰이 없으면 keyword 전체로 fallback.
            tokens = [t for t in keyword.split() if len(t) >= 2]
            if tokens:
                token_filter = Q()
                for token in tokens:
                    token_filter |= Q(question__icontains=token) | Q(answer__icontains=token)
                qs = qs.filter(token_filter)
            else:
                qs = qs.filter(Q(question__icontains=keyword) | Q(answer__icontains=keyword))
        return list(await qs.order_by("category", "sort_order", "id"))

    async def get(self, faq_id: int) -> ChatbotFaq | None:
        return await self._model.get_or_none(id=faq_id, is_active=True)


class ChatbotSessionRepository:
    def __init__(self) -> None:
        self._model = ChatbotSession

    async def create(self, user_id: int, title: str | None = None) -> ChatbotSession:
        return await self._model.create(user_id=user_id, title=title)

    async def get_owned(self, session_id: int, user_id: int) -> ChatbotSession | None:
        return await self._model.get_or_none(id=session_id, user_id=user_id)

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[ChatbotSession]:
        return list(await self._model.filter(user_id=user_id).order_by("-last_message_at", "-started_at").limit(limit))

    async def touch(self, session: ChatbotSession, message_increment: int = 1) -> ChatbotSession:
        from datetime import datetime

        from app.core import config

        session.last_message_at = datetime.now(config.TIMEZONE)
        session.message_count += message_increment
        await session.save(update_fields=["last_message_at", "message_count"])
        return session


class ChatbotMessageRepository:
    def __init__(self) -> None:
        self._model = ChatbotMessage

    async def create(self, data: dict[str, Any]) -> ChatbotMessage:
        return await self._model.create(**data)

    async def list_for_session(self, session_id: int) -> list[ChatbotMessage]:
        return list(await self._model.filter(session_id=session_id).order_by("created_at"))
