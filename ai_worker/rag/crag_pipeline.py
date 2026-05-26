"""
CRAG (Corrective RAG) + LangGraph
======================================
설치 :
    pip install langgraph langchain langchain-openai tavily-python

환경변수 (.env):
    OPENAI_API_KEY=sk-...
    TAVILY_API_KEY=tvly-... 
"""

import os
import json
from pathlib import Path
from typing import TypedDict, Literal, Optional

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from rank_bm25 import BM25Okapi
from kiwipiepy import Kiwi
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from tavily import TavilyClient

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE        = Path(__file__).parent
CHROMA_DIR  = BASE / "chroma_db"
CHUNKS_PATH = BASE / "output" / "chunks.json"

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL       = "gpt-4o-mini"
COLLECTION_NAME = "chronic_disease_rag"
TOP_K           = 5
RRF_K           = 60

# ─────────────────────────────────────────────
# 환경변수 로드
# ─────────────────────────────────────────────
def load_env(base: Path):
    env_path = base.parent.parent / "envs" / ".local.env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

load_env(BASE)

# ─────────────────────────────────────────────
# 클라이언트 초기화
# ─────────────────────────────────────────────
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False),
)
collection = chroma_client.get_collection(name=COLLECTION_NAME)
llm        = ChatOpenAI(model=LLM_MODEL, temperature=0, streaming=True)

# Tavily (웹 검색) 
tavily_key    = os.environ.get("TAVILY_API_KEY", "")
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

with open(CHUNKS_PATH, encoding="utf-8") as f:
    chunks = json.load(f)

# ─────────────────────────────────────────────
# 형태소 분석 + BM25
# ─────────────────────────────────────────────
kiwi = Kiwi()

def tokenize(text: str) -> list[str]:
    tokens = []
    for token in kiwi.tokenize(text):
        if token.tag.startswith(("NN", "VV", "VA", "SL")):
            tokens.append(token.form)
    return tokens if tokens else text.split()

print("BM25 인덱스 구축 중...")
bm25 = BM25Okapi([tokenize(c["content"]) for c in chunks])
print("준비 완료!\n")

# ─────────────────────────────────────────────
# Hybrid 검색
# ─────────────────────────────────────────────
def hybrid_search(query: str, top_k: int = TOP_K) -> list[dict]:
    # Dense
    emb     = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    results = collection.query(
        query_embeddings=[emb.data[0].embedding],
        n_results=top_k * 2,
        include=["documents", "metadatas", "distances"],
    )
    dense = [
        {"content": d, "metadata": m, "score": 1 - s}
        for d, m, s in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]

    # Sparse (BM25)
    scores  = bm25.get_scores(tokenize(query))
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: top_k * 2]
    sparse  = [
        {
            "content":  chunks[i]["content"],
            "metadata": {k: v for k, v in chunks[i].items() if k != "content"},
            "score":    float(scores[i]),
        }
        for i in top_idx
    ]

    # RRF 병합
    rrf_scores:  dict[str, float] = {}
    content_map: dict[str, dict]  = {}
    for rank, item in enumerate(dense):
        key              = item["content"][:100]
        rrf_scores[key]  = rrf_scores.get(key, 0) + 1 / (RRF_K + rank + 1)
        content_map[key] = item
    for rank, item in enumerate(sparse):
        key              = item["content"][:100]
        rrf_scores[key]  = rrf_scores.get(key, 0) + 1 / (RRF_K + rank + 1)
        if key not in content_map:
            content_map[key] = item

    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
    return [content_map[k] for k in sorted_keys[:top_k]]


# ─────────────────────────────────────────────
# LangGraph 상태 정의
# ─────────────────────────────────────────────
class CRAGState(TypedDict):
    question:             str            # 사용자 질문
    prediction_result:    Optional[dict] # ML 예측 결과 (당뇨/고혈압/심혈관 위험도)
    retrieved_context:    list[dict]     # 검색된 청크 리스트 (documents → retrieved_context)
    web_results:          list[str]      # 웹 검색 결과
    final_recommendation: str            # 최종 답변 (generation → final_recommendation)
    rewrite_count:        int            # 쿼리 재작성 횟수 (무한루프 방지)


# ─────────────────────────────────────────────
# 노드 1: 문서 검색
# ML 예측 결과 있으면 쿼리에 반영
# ─────────────────────────────────────────────
def retrieve(state: CRAGState) -> dict:
    question       = state["question"]
    prediction     = state.get("prediction_result") or {}

    # ML 예측 결과 있으면 고위험 질환 쿼리에 추가

    #한국어 매핑
    DISEASE_KO = {
        "diabetes":       "당뇨병",
        "hypertension":   "고혈압",
        "cardiovascular": "심혈관질환",
    }

    if prediction:
        high_risk = [
            DISEASE_KO.get(disease, disease)
            for disease, risk in prediction.items()
            if isinstance(risk, (int, float)) and risk >= 50
        ]
        if high_risk:
            query = f"{question} {' '.join(high_risk)} 위험군 관련"
        else:
            query = question
    else:
        query = question

    print(f"\n[검색] '{query}'")
    docs = hybrid_search(query)
    print(f"  → {len(docs)}개 청크 검색됨")
    for i, d in enumerate(docs):
        meta = d.get("metadata", {})
        print(f"    [{i+1}] {meta.get('source_id','?')} | {meta.get('section_title','?')}")

    return {"retrieved_context": docs}


# ─────────────────────────────────────────────
# 노드 2: 문서 관련성 판단 (Grader)
# ─────────────────────────────────────────────
GRADE_PROMPT = """당신은 검색된 문서가 사용자 질문과 관련 있는지 판단하는 평가자입니다.

질문: {question}
문서 내용: {content}

이 문서가 질문에 답하는 데 관련이 있으면 "yes", 없으면 "no"만 답하세요."""

def grade_documents(state: CRAGState) -> dict:
    print("\n[관련성 판단]")
    question      = state["question"]
    docs          = state["retrieved_context"]
    relevant_docs = []

    for doc in docs:
        response = llm.invoke([
            HumanMessage(content=GRADE_PROMPT.format(
                question=question,
                content=doc["content"][:500],
            ))
        ])
        grade = response.content.strip().lower()
        meta  = doc.get("metadata", {})
        print(f"  {meta.get('section_title','?')[:30]} → {grade}")
        if "yes" in grade:
            relevant_docs.append(doc)

    print(f"  관련 문서: {len(relevant_docs)}/{len(docs)}개")
    return {"retrieved_context": relevant_docs}


# ─────────────────────────────────────────────
# 노드 3: 쿼리 재작성
# ─────────────────────────────────────────────
REWRITE_PROMPT = """사용자의 질문을 의학 문서 검색에 더 적합하도록 재작성하세요.
전문 용어를 사용하고, 핵심 키워드를 명확히 해주세요.
재작성된 질문만 출력하세요.

원본 질문: {question}"""

def rewrite_query(state: CRAGState) -> dict:
    print("\n[쿼리 재작성]")
    response     = llm.invoke([
        HumanMessage(content=REWRITE_PROMPT.format(question=state["question"]))
    ])
    new_question = response.content.strip()
    print(f"  원본: {state['question']}")
    print(f"  재작성: {new_question}")

    docs = hybrid_search(new_question)
    return {
        "question":      new_question,
        "retrieved_context": docs,
        "rewrite_count": state.get("rewrite_count", 0) + 1,
    }


# ─────────────────────────────────────────────
# 노드 4: 웹 검색 보완
# ─────────────────────────────────────────────
def web_search(state: CRAGState) -> dict:
    print("\n[웹 검색 보완]")

    if not tavily_client:
        print("  TAVILY_API_KEY 없음 → 웹 검색 스킵")
        return {"web_results": []}

    try:
        results     = tavily_client.search(query=state["question"], max_results=3)
        web_results = [r["content"] for r in results.get("results", [])]
        print(f"  웹 검색 결과: {len(web_results)}개")
        return {"web_results": web_results}
    except Exception as e:
        print(f"  웹 검색 오류: {e}")
        return {"web_results": []}


# ─────────────────────────────────────────────
# 노드 5: 답변 생성
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 만성질환(고혈압·당뇨·이상지질혈증) 생활습관 관리 서비스의 전문 챗봇입니다.

## 답변 규칙
1. 반드시 제공된 [참고 자료]만을 근거로 답변하세요.
2. 참고 자료에 없는 내용은 "제공된 자료에서 확인할 수 없습니다"라고 답하세요.
3. "~할 수 있습니다", "~권고됩니다" 형식으로 답하세요.
4. 한국어로 답변하세요.
5. 복잡한 의학 용어는 쉽게 풀어서 설명하세요.
6. 답변 마지막에 반드시 면책 문구를 포함하세요.

## 면책 문구 (항상 포함)
> ⚠️ 본 답변은 일반적인 건강 정보 제공을 목적으로 하며, 의료적 진단·처방·치료를 대체하지 않습니다. 정확한 진단과 치료는 반드시 의료 전문가에게 문의하세요."""

def generate(state: CRAGState) -> dict:
    print("\n[답변 생성]")

    # 컨텍스트 구성 (RAG 청크 + ML 예측 결과 + 웹 검색 결과)
    context_parts = []

    # ML 예측 결과 있으면 컨텍스트에 포함
    prediction = state.get("prediction_result") or {}
    if prediction:
        pred_str = "\n".join([f"- {k}: {v}%" for k, v in prediction.items()])
        context_parts.append(f"[사용자 질병 위험도]\n{pred_str}")

    for i, doc in enumerate(state["retrieved_context"]):
        meta     = doc.get("metadata", {})
        source   = meta.get("source_id", "?")
        title    = meta.get("section_title", "?")
        pages    = meta.get("source_pages", "")
        page_str = f" (p.{pages})" if pages and pages != "?" else ""
        context_parts.append(f"[자료 {i+1}] {source} — {title}{page_str}\n{doc['content']}")

    for i, web in enumerate(state.get("web_results", [])):
        context_parts.append(f"[웹 자료 {i+1}]\n{web}")

    context     = "\n\n".join(context_parts) if context_parts else "관련 자료를 찾을 수 없습니다."
    user_prompt = f"[참고 자료]\n{context}\n\n---\n\n[질문]\n{state['question']}\n\n위 참고 자료를 바탕으로 질문에 답변해주세요."

    print("\n  🤖 답변:")
    print("  " + "─" * 55)
    full_answer = ""
    for chunk in llm.stream([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content
    print("\n  " + "─" * 55)

    return {"final_recommendation": full_answer}


# ─────────────────────────────────────────────
# 엣지: 관련성 판단 후 분기
# ─────────────────────────────────────────────
def decide_next(state: CRAGState) -> Literal["generate", "rewrite_query", "web_search"]:
    docs          = state["retrieved_context"]
    rewrite_count = state.get("rewrite_count", 0)

    if len(docs) >= 2:
        print("\n[분기] 관련 문서 충분 → 답변 생성")
        return "generate"

    if rewrite_count >= 1:
        print("\n[분기] 재작성 후에도 부족 → 웹 검색")
        return "web_search"

    print("\n[분기] 관련 문서 부족 → 쿼리 재작성")
    return "rewrite_query"


# ─────────────────────────────────────────────
# LangGraph 그래프 구성
# ─────────────────────────────────────────────
def build_crag_graph():
    graph = StateGraph(CRAGState)

    graph.add_node("retrieve",        retrieve)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("rewrite_query",   rewrite_query)
    graph.add_node("web_search",      web_search)
    graph.add_node("generate",        generate)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade_documents")

    graph.add_conditional_edges(
        "grade_documents",
        decide_next,
        {
            "generate":      "generate",
            "rewrite_query": "rewrite_query",
            "web_search":    "web_search",
        },
    )

    graph.add_edge("rewrite_query", "grade_documents")
    graph.add_edge("web_search",    "generate")
    graph.add_edge("generate",      END)

    return graph.compile()


# ─────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────
TEST_CASES = [
    # (질문, ML 예측 결과)
    ("당뇨병 환자의 혈당 조절 목표가 어떻게 돼?", None),
    ("고혈압 환자는 혈압을 얼마나 낮춰야 해?",    None),
    ("챌린지 인증 실패하면 어떻게 해?",           None),
    # ML 예측 결과 있는 경우 테스트
    ("나한테 맞는 챌린지 추천해줘", {
        "diabetes":       62.3,
        "hypertension":   44.1,
        "cardiovascular": 38.7,
    }),
]

if __name__ == "__main__":
    print("=" * 60)
    print("  CRAG + LangGraph 파이프라인 테스트")
    print("=" * 60)

    crag = build_crag_graph()

    for question, prediction in TEST_CASES:
        print(f"\n{'=' * 60}")
        print(f"  ❓ 질문: {question}")
        if prediction:
            print(f"  📊 ML 예측: {prediction}")
        print(f"{'=' * 60}")

        initial_state: CRAGState = {
            "question":             question,
            "prediction_result":    prediction,
            "retrieved_context":    [],
            "web_results":          [],
            "final_recommendation": "",
            "rewrite_count":        0,
        }

        # stream()으로 각 노드 실행 상태 추적 (팀원 문서 참고)
        for step in crag.stream(initial_state):
            node_name = list(step.keys())[0]
            if node_name not in ("generate",):  # generate는 스트리밍으로 이미 출력
                pass  # 각 노드 실행 확인용

    print(f"\n{'=' * 60}")
    print("  ✅ CRAG 테스트 완료!")
    print("=" * 60)
