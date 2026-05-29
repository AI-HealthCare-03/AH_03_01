"""챗봇 RAG seam — ChatRAGGraph 실행 어댑터.

호출 측(`app/services/chatbot.py`) 은 본 모듈의 `RAGAnswer` 인터페이스만 의존한다.
실제 RAG/LLM 로직은 `app/graphs/chat_rag_graph.py` 의 LangGraph 가 수행하며,
본 모듈은 그래프 결과(`ChatRAGResult`) 를 서비스 응답용 dataclass(`RAGAnswer`) 로 변환한다.

이전(rag-stub-v0): 룰 기반 폴백 — RAGDocument 가 비어 있어도 동작하도록 placeholder.
현재(chatragraph-v1): ChatRAGGraph 실행 — PGVector 하이브리드 검색 + LLM + 2-stage evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # ChatRAGResult 는 타입 힌트에만 사용. 런타임 import 는 answer() 안에서 lazy 로 처리한다.
    # app.services.ml.__init__ ↔ app.graphs.chat_rag_graph 순환(app.graphs 가 app.services.ml.retrieval
    # 을 import 하면 ml/__init__ 이 평가되며 chatbot_rag → chat_rag_graph 로 되돌아오는 사이클) 방지.
    from app.graphs.chat_rag_graph import ChatRAGResult


# chat_rag_graph 의 동일 상수와 정렬 (양쪽이 자체 모듈에서 직접 사용).
MEDICAL_DISCLAIMER = "본 답변은 의학적 진단을 대체하지 않습니다."


@dataclass(slots=True)
class RAGSource:
    title: str | None = None
    url: str | None = None
    document_id: int | None = None
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        # url 은 항상 None 인 죽은 필드 — 응답·DB 직렬화에서 제거.
        # 외부 URL 자료가 들어오면 향후 부활.
        return {
            "title": self.title,
            "document_id": self.document_id,
            "snippet": self.snippet,
        }


@dataclass(slots=True)
class RAGAnswer:
    """ChatRAGGraph 결과를 서비스 레이어가 소비하는 dataclass.

    기존 필드(answer/sources/confidence/model_version/fallback) 는 보존하고,
    API 계약(`RAG/LangGraph_API계약_chat_v1.md`) 의 신규 응답 필드를 추가.
    """

    # ── 기존 필드 ───────────────────────────────────
    answer: str
    sources: list[RAGSource] = field(default_factory=list)
    confidence: float = 0.0
    model_version: str = "chatragraph-v1"
    fallback: bool = False  # is_fallback 의 기존 명칭 (응답 시 is_fallback 으로 매핑)

    # ── 신규 필드 (ChatRAGGraph 결과 표현) ────────────
    intent: str | None = None
    needs_health_data: bool = False
    missing_fields: list[str] = field(default_factory=list)
    action_hint: str | None = None
    eval_revision_count: int | None = None
    disclaimer: str = MEDICAL_DISCLAIMER


# 컨텍스트 스니펫 길이 (출처 카드용)
_SNIPPET_MAX_LEN = 200


def _to_source(c: Any) -> RAGSource:
    """RetrievedChunk → RAGSource 어댑터.

    chunk_text 의 앞부분만 스니펫으로 사용 (길이 _SNIPPET_MAX_LEN 자 제한).
    url 은 내부 진료지침/서비스 가이드 답변에선 항상 None — 응답 직렬화 시 제거.
    """
    text = getattr(c, "chunk_text", "") or ""
    snippet = text[:_SNIPPET_MAX_LEN] + ("…" if len(text) > _SNIPPET_MAX_LEN else "")
    return RAGSource(
        title=getattr(c, "title", None),
        url=None,
        document_id=getattr(c, "document_id", None),
        snippet=snippet,
    )


def _result_to_answer(r: ChatRAGResult) -> RAGAnswer:
    return RAGAnswer(
        answer=r.answer,
        sources=[_to_source(c) for c in r.sources],
        confidence=r.confidence,
        model_version=r.model_version,
        fallback=r.is_fallback,
        intent=r.intent,
        needs_health_data=r.needs_health_data,
        missing_fields=list(r.missing_fields),
        action_hint=r.action_hint,
        eval_revision_count=r.eval_revision_count,
        disclaimer=r.disclaimer,
    )


class ChatbotRAG:
    """ChatRAGGraph 실행 진입점.

    호출:
        rag = ChatbotRAG()
        result: RAGAnswer = await rag.answer(query="...", user_id=42, thread_id="42")
    """

    model_version = "chatragraph-v1"

    async def answer(self, *, query: str, user_id: Any, thread_id: str) -> RAGAnswer:
        """ChatRAGGraph 1회 실행 → RAGAnswer.

        Args:
            query: 사용자 질문
            user_id: 인증된 사용자 id (health_data 조회용). 프로젝트의 User PK 가
                int(과거) → UUID(현행) 전환 잔여 영역에 걸쳐 있어 Any 로 받아 Tortoise
                filter 가 처리하게 한다.
            thread_id: LangGraph thread (1단계는 str(session.id) 재사용)
        """
        # Lazy import — 모듈 로딩 시점의 순환(app.services.ml.__init__ ↔ app.graphs) 방지.
        from app.graphs.chat_rag_graph import run_chat_rag

        result = await run_chat_rag(question=query, user_id=user_id, thread_id=thread_id)
        return _result_to_answer(result)
