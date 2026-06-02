from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

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


@chatbot_router.post(
    "/messages/stream",
    status_code=status.HTTP_200_OK,
)
async def stream_chat_message(
    body: ChatMessageRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ChatbotConversationService, Depends(ChatbotConversationService)],
    mode: Annotated[str, Query(description="rag (스트리밍은 rag 전용)")] = "rag",
) -> StreamingResponse:
    """SSE 스트리밍 챗봇 응답 — meta → stage* → token* → done (실패 시 error) 이벤트.

    비스트리밍 POST /messages 와 동일 계약·트랜잭션 경계를 따르되, 그래프 진행 단계와
    최종 답변 토큰을 실시간으로 흘려보낸다. 응답 본문 shape(done 이벤트)은
    ChatMessageResponse 와 동일하다.

    헤더: X-Accel-Buffering=no 로 nginx 버퍼링을 무력화하려 시도하나, 운영 nginx 의
    `proxy_buffering off` (해당 location) 설정이 함께 필요할 수 있다.
    """
    generator: AsyncGenerator[str, None] = service.handle_message_stream(user, mode, body)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
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
