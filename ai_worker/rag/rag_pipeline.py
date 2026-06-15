"""
RAG 프롬프트 + LLM 답변 생성 (스트리밍)
======================================

설치:
    pip install chromadb openai rank_bm25 kiwipiepy

기능:
    - Hybrid 검색 (Dense + BM25)으로 관련 청크 검색
    - 검색된 청크를 컨텍스트로 LLM에 전달
    - 스트리밍 방식으로 답변 생성
    - 의료 면책 문구 자동 포함
"""

import json
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from kiwipiepy import Kiwi
from openai import OpenAI
from rank_bm25 import BM25Okapi

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE = Path(__file__).parent
CHROMA_DIR = BASE / "chroma_db"
CHUNKS_PATH = BASE / "output" / "chunks.json"

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
COLLECTION_NAME = "chronic_disease_rag"
TOP_K = 5  # 검색할 청크 수
RRF_K = 60  # RRF 상수

# ─────────────────────────────────────────────
# 프롬프트 템플릿
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 만성질환(고혈압·당뇨·이상지질혈증) 생활습관 관리 서비스의 건강 도우미입니다.
사용자가 건강 걱정을 편하게 털어놓을 수 있도록, 따뜻하고 친근한 말투로 대화합니다.

## 역할
- 사용자의 건강 관련 질문에 신뢰할 수 있는 의학 근거 기반으로 답변합니다.
- 서비스 이용 방법에 대한 질문에도 친절하게 안내합니다.

## 말투 원칙
- 딱딱한 나열식 설명보다 대화하듯 자연스럽게 설명하세요.
- "~하시면 좋아요", "~해보시는 건 어떨까요?" 같은 부드러운 표현을 활용하세요.
- 사용자의 상황을 공감하며 시작하면 더욱 좋습니다. (예: "혈압이 높으셔서 걱정되실 것 같아요.")
- 지나치게 격식 차린 문어체보다는 따뜻한 구어체를 선호합니다.

## 위험도 점수 해석 기준 (사용자가 점수를 언급한 경우 반드시 이 기준을 따르세요)
서비스의 위험도 점수는 0~100 사이 숫자이며, 숫자가 클수록 위험도가 높습니다.
- 0~20점: 매우 낮음
- 21~40점: 낮음
- 41~60점: 보통
- 61~80점: 높음
- 81~100점: 매우 높음

사용자가 위험도 점수를 언급한 경우, 위 기준으로 정확히 해석한 뒤 답변하세요.
예) "위험도 34%"는 **낮음** 수준입니다. "위험도 높다"는 등의 잘못된 해석을 해서는 안 됩니다.

## 답변 규칙
1. 반드시 제공된 [참고 자료]만을 근거로 답변하세요.
2. 참고 자료에 없는 내용은 "제공된 자료에서 확인할 수 없습니다"라고 답하세요.
3. 확정적·단정적 표현 대신 "~할 수 있어요", "~권장드려요" 형식으로 답하세요.
4. 답변은 한국어로 작성하세요.
5. 복잡한 의학 용어는 쉽게 풀어서 설명하세요.
6. 답변 마지막에 반드시 면책 문구를 포함하세요.

## 면책 문구 (항상 포함)
> ⚠️ 본 답변은 일반적인 건강 정보 제공을 목적으로 하며, 의료적 진단·처방·치료를 대체하지 않습니다. 정확한 진단과 치료는 반드시 의료 전문가에게 문의하세요."""

USER_PROMPT_TEMPLATE = """[참고 자료]
{context}

---

[질문]
{question}

위 참고 자료를 바탕으로 질문에 답변해주세요."""


# ─────────────────────────────────────────────
# 초기화
# ─────────────────────────────────────────────
def load_env(base: Path):
    env_path = base.parent.parent / "envs" / ".local.env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def init_clients():
    load_env(BASE)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 없음. .env 파일 확인하세요.")
    openai_client = OpenAI(api_key=api_key)
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return openai_client, chroma_client


# ─────────────────────────────────────────────
# 형태소 분석
# ─────────────────────────────────────────────
kiwi = Kiwi()


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in kiwi.tokenize(text):
        if token.tag.startswith(("NN", "VV", "VA", "SL")):
            tokens.append(token.form)
    return tokens if tokens else text.split()


# ─────────────────────────────────────────────
# BM25 인덱스
# ─────────────────────────────────────────────
def build_bm25_index(chunks: list[dict]):
    tokenized_corpus = [tokenize(c["content"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    return bm25


# ─────────────────────────────────────────────
# Hybrid 검색
# ─────────────────────────────────────────────
def dense_search(collection, openai_client, query, top_k):
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    embedding = response.data[0].embedding
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        strict=False,
    ):
        output.append({"content": doc, "metadata": meta, "score": 1 - dist})
    return output


def sparse_search(bm25, chunks, query, top_k):
    scores = bm25.get_scores(tokenize(query))
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [
        {
            "content": chunks[idx]["content"],
            "metadata": {k: v for k, v in chunks[idx].items() if k != "content"},
            "score": float(scores[idx]),
        }
        for idx in top_indices
    ]


def rrf_merge(dense_results, sparse_results, top_k, k=RRF_K):
    rrf_scores = {}
    content_map = {}
    for rank, item in enumerate(dense_results):
        key = item["content"][:100]
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k + rank + 1)
        content_map[key] = item
    for rank, item in enumerate(sparse_results):
        key = item["content"][:100]
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k + rank + 1)
        if key not in content_map:
            content_map[key] = item
    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
    return [content_map[key] for key in sorted_keys[:top_k]]


def hybrid_search(collection, openai_client, bm25, chunks, query, top_k=TOP_K):
    dense_results = dense_search(collection, openai_client, query, top_k * 2)
    sparse_results = sparse_search(bm25, chunks, query, top_k * 2)
    return rrf_merge(dense_results, sparse_results, top_k)


# ─────────────────────────────────────────────
# 컨텍스트 구성
# ─────────────────────────────────────────────
def build_context(search_results: list[dict]) -> str:
    """검색 결과를 LLM 컨텍스트 문자열로 변환"""
    parts = []
    for i, item in enumerate(search_results):
        meta = item.get("metadata", {})
        source = meta.get("source_id", "?")
        title = meta.get("section_title", "?")
        pages = meta.get("source_pages", "")
        page_str = f" (p.{pages})" if pages and pages != "?" else ""

        parts.append(f"[자료 {i + 1}] {source} — {title}{page_str}\n{item['content']}")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────
# LLM 스트리밍 답변 생성
# ─────────────────────────────────────────────
def generate_answer_stream(openai_client, question: str, context: str):
    """스트리밍 방식으로 답변 생성"""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )

    stream = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        temperature=0.3,  # 낮을수록 일관된 답변
        max_tokens=1000,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# ─────────────────────────────────────────────
# RAG 파이프라인 전체 실행
# ─────────────────────────────────────────────
def rag_answer(
    question: str,
    collection,
    openai_client,
    bm25,
    chunks: list[dict],
    verbose: bool = True,
) -> str:
    """
    질문 → Hybrid 검색 → 컨텍스트 구성 → LLM 스트리밍 답변
    verbose=True: 검색된 청크 출처 출력
    """
    # 1. Hybrid 검색
    search_results = hybrid_search(collection, openai_client, bm25, chunks, question)

    # 2. 출처 출력 (verbose 모드)
    if verbose:
        print("\n  📚 참고 청크:")
        for i, item in enumerate(search_results):
            meta = item.get("metadata", {})
            print(f"    [{i + 1}] {meta.get('source_id', '?')} | {meta.get('section_title', '?')}")
        print()

    # 3. 컨텍스트 구성
    context = build_context(search_results)

    # 4. 스트리밍 답변 생성
    print("  🤖 답변:")
    print("  " + "─" * 55)
    full_answer = ""
    for token in generate_answer_stream(openai_client, question, context):
        print(token, end="", flush=True)
        full_answer += token
    print("\n  " + "─" * 55)

    return full_answer


# ─────────────────────────────────────────────
# 테스트 실행
# ─────────────────────────────────────────────
TEST_QUESTIONS = [
    "당뇨병 환자의 혈당 조절 목표가 어떻게 돼?",
    "고혈압 환자는 혈압을 얼마나 낮춰야 해?",
    "챌린지 인증 실패하면 어떻게 해?",
]

if __name__ == "__main__":
    print("=" * 60)
    print("  RAG 파이프라인 테스트 (프롬프트 + LLM 스트리밍)")
    print("=" * 60)

    # 초기화
    openai_client, chroma_client = init_clients()
    collection = chroma_client.get_collection(name=COLLECTION_NAME)

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\n  컬렉션: {collection.count()}개 청크")
    print("  BM25 인덱스 구축 중...")
    bm25 = build_bm25_index(chunks)
    print("  준비 완료!\n")

    for question in TEST_QUESTIONS:
        print(f"\n{'=' * 60}")
        print(f"  ❓ 질문: {question}")
        print(f"{'=' * 60}")
        rag_answer(question, collection, openai_client, bm25, chunks)

    print(f"\n{'=' * 60}")
    print("  ✅ 테스트 완료!")
    print("=" * 60)
