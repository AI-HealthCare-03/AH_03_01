from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.chatbot import (
    ChatMessageItem,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionDetailResponse,
    ChatSessionListItem,
    ChatSessionListResponse,
    FaqListResponse,
    FaqResponse,
)
from app.models.chatbot import FaqCategory
from app.models.users import User
from app.services.chatbot import ChatbotConversationService, ChatbotFaqService

chatbot_router = APIRouter(prefix="/chat", tags=["chatbot"])


@chatbot_router.get("/faqs", response_model=FaqListResponse, status_code=status.HTTP_200_OK)
async def list_faqs(
    _: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChatbotFaqService, Depends(ChatbotFaqService)],
    category: Annotated[FaqCategory | None, Query()] = None,
    keyword: Annotated[str | None, Query()] = None,
) -> Response:
    faqs = await service.list(category, keyword)
    payload = FaqListResponse(faqs=[FaqResponse.model_validate(f) for f in faqs])
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@chatbot_router.post(
    "/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def send_chat_message(
    body: ChatMessageRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChatbotConversationService, Depends(ChatbotConversationService)],
    mode: Annotated[str, Query(description="faq|rag")] = "rag",
) -> Response:
    payload = await service.handle_message(user, mode, body)
    # ChatMessageResponse 로 wrap 하면 disclaimer default 가 자동 적용됨.
    return Response(
        ChatMessageResponse(**payload).model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


@chatbot_router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_chat_sessions(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChatbotConversationService, Depends(ChatbotConversationService)],
) -> Response:
    sessions = await service.list_sessions(user)
    payload = ChatSessionListResponse(
        sessions=[
            ChatSessionListItem(
                id=s.id,
                title=s.title,
                started_at=s.started_at,
                ended_at=s.ended_at,
                last_message_at=s.last_message_at,
                message_count=s.message_count,
            )
            for s in sessions
        ]
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@chatbot_router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_session(
    session_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChatbotConversationService, Depends(ChatbotConversationService)],
) -> Response:
    session, messages = await service.get_session_messages(user, session_id)
    payload = ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        started_at=session.started_at,
        ended_at=session.ended_at,
        messages=[
            ChatMessageItem(
                id=m.id,
                role=m.role,
                message_type=m.message_type,
                content=m.content,
                faq_id=m.faq_id,
                sources=list(m.sources or []),
                confidence=m.confidence,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
    return Response(payload.model_dump(mode="json"), status_code=status.HTTP_200_OK)
