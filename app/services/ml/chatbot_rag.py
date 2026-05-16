"""챗봇 RAG/LLM 게이트웨이 스텁.

현재 ai_worker 의 임베딩 인코더 / LLM 응답 모델이 준비되지 않아 키워드 기반 폴백을 사용한다.
실제 모델이 준비되면 `ChatbotRAG.answer()` 본문만 ai_worker 호출 + RAGDocument 벡터 검색으로 교체.
호출 측(app/services/chatbot.py) 은 본 모듈의 인터페이스(`RAGAnswer`)만 의존한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RAGSource:
    title: str | None = None
    url: str | None = None
    document_id: int | None = None
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "document_id": self.document_id,
            "snippet": self.snippet,
        }


@dataclass(slots=True)
class RAGAnswer:
    answer: str
    sources: list[RAGSource] = field(default_factory=list)
    confidence: float = 0.0
    model_version: str = "rag-stub-v0"
    fallback: bool = True


FALLBACK_MESSAGE = (
    "현재 챗봇 학습 자료가 준비 중이라 정확한 답변을 드리기 어렵습니다. "
    "곧 RAG 기반 답변이 제공될 예정입니다. 시급한 건강 관련 문의는 의료 전문가와 상담해 주세요."
)


class ChatbotRAG:
    """ai_worker 의 임베딩+LLM 호출 단일 진입점.

    현재 구현: 룰 기반 폴백 (RAGDocument 컬렉션이 비어 있어도 동작).
    향후: ai_worker 의 임베딩 인코더로 query → vector → RAGDocument 코사인 유사도 검색 →
          LLM 으로 컨텍스트 기반 응답 생성. 실패/타임아웃 시 폴백 메시지 반환.
    """

    model_version = "rag-stub-v0"

    async def answer(self, *, query: str, top_k: int = 5) -> RAGAnswer:
        # TODO(ai_worker): 1) ai_worker 임베딩 호출 2) RAGDocument <=> 검색
        # 3) ai_worker LLM 응답 생성. 본 스텁은 무조건 폴백 응답.
        return RAGAnswer(
            answer=FALLBACK_MESSAGE,
            sources=[],
            confidence=0.0,
            model_version=self.model_version,
            fallback=True,
        )

    async def embed(self, text: str) -> list[float]:
        # 임베딩 인코더 스텁. 실제 구현은 ai_worker 의 sentence-transformers 모델 호출.
        return []
