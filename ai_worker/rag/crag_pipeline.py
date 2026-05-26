"""
CRAG (Corrective RAG) + LangGraph
======================================
설치:
    pip install langgraph langchain langchain-openai tavily-python

환경변수 (.env):
    OPENAI_API_KEY=sk-...
    TAVILY_API_KEY=tvly-...

워크플로우:
    Question
      ↓
    Retrieve (Hybrid 문서 검색)
      ↓
    Generate (LLM 답변 생성)
      ↓
    Evaluator (답변 품질 평가)
      ├→ Pass          → Answer (최종 답변)
      ├→ 정보 불충분    → 웹 검색 → Add context → Retrieve (루프)
      └→ 프롬프트 수정  → Generate 재시도
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

EMBEDDING_MODEL  = "text-embedding-3-small"
LLM_MODEL        = "gpt-4o-mini"
COLLECTION_NAME  = "chronic_disease_rag"
TOP_K            = 5
RRF_K            = 60
MAX_RETRY        = 2   # 평가 후 재시도 최대 횟수 (무한루프 방지)

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
    prediction_result:    Optional[dict] # ML 예측 결과
    retrieved_context:    list[dict]     # 검색된 청크
    web_results:          list[str]      # 웹 검색 결과
    final_recommendation: str            # 최종 답변
    eval_feedback:        str            # 평가자 피드백 (프롬프트 수정용)
    retry_count:          int            # 재시도 횟수 (무한루프 방지)


# ─────────────────────────────────────────────
# 노드 1: 문서 검색 (Retrieve)
# ─────────────────────────────────────────────
DISEASE_KO = {
    "diabetes":       "당뇨병",
    "hypertension":   "고혈압",
    "cardiovascular": "심혈관질환",
}

def retrieve(state: CRAGState) -> dict:
    question   = state["question"]
    prediction = state.get("prediction_result") or {}

    # ML 고위험 질환 한국어로 쿼리 보강
    if prediction:
        high_risk = [
            DISEASE_KO.get(d, d)
            for d, r in prediction.items()
            if isinstance(r, (int, float)) and r >= 50
        ]
        query = f"{question} {' '.join(high_risk)} 위험군 관련" if high_risk else question
    else:
        query = question

    # 웹 검색 결과 있으면 컨텍스트에 추가된 상태 유지
    existing_context = state.get("retrieved_context", [])

    print(f"\n[검색] '{query}'")
    docs = hybrid_search(query)
    print(f"  → {len(docs)}개 청크 검색됨")
    for i, d in enumerate(docs):
        meta = d.get("metadata", {})
        print(f"    [{i+1}] {meta.get('source_id','?')} | {meta.get('section_title','?')}")

    # 기존 컨텍스트(웹 검색 결과 포함) + 새 검색 결과 병합
    return {"retrieved_context": existing_context + docs}


# ─────────────────────────────────────────────
# 노드 2: 답변 생성 (Generate)
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

    context_parts = []

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

    context = "\n\n".join(context_parts) if context_parts else "관련 자료를 찾을 수 없습니다."

    # 평가자 피드백 있으면 프롬프트에 반영
    feedback    = state.get("eval_feedback", "")
    extra_guide = f"\n\n## 추가 지침 (이전 답변 보완)\n{feedback}" if feedback else ""

    user_prompt = f"[참고 자료]\n{context}\n\n---\n\n[질문]\n{state['question']}\n\n위 참고 자료를 바탕으로 질문에 답변해주세요."

    print("\n  🤖 답변:")
    print("  " + "─" * 55)
    full_answer = ""
    for chunk in llm.stream([
        SystemMessage(content=SYSTEM_PROMPT + extra_guide),
        HumanMessage(content=user_prompt),
    ]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content
    print("\n  " + "─" * 55)

    return {"final_recommendation": full_answer}


# ─────────────────────────────────────────────
# 노드 3: 답변 품질 평가 (Evaluator)
# ─────────────────────────────────────────────
EVAL_PROMPT = """당신은 챗봇 답변의 품질을 평가하는 전문가입니다.

[사용자 질문]
{question}

[챗봇 답변]
{answer}

아래 기준으로 평가하고 결과만 출력하세요:

1. 답변이 질문에 충분히 답하고 있으면 → "pass"
2. 답변이 너무 일반적이거나 정보가 부족하면 → "insufficient: (부족한 내용 한 줄 설명)"
3. 답변의 방향이나 형식이 잘못됐으면 → "prompt_fix: (수정이 필요한 내용 한 줄 설명)"

반드시 위 세 가지 중 하나로만 답하세요."""

def evaluate_answer(state: CRAGState) -> dict:
    print("\n[평가자 Evaluator]")

    response = llm.invoke([
        HumanMessage(content=EVAL_PROMPT.format(
            question=state["question"],
            answer=state["final_recommendation"][:800],
        ))
    ])
    result = response.content.strip().lower()
    print(f"  평가 결과: {result}")

    if result.startswith("insufficient"):
        feedback = result.replace("insufficient:", "").strip()
        return {"eval_feedback": feedback}
    elif result.startswith("prompt_fix"):
        feedback = result.replace("prompt_fix:", "").strip()
        return {"eval_feedback": feedback}
    else:
        return {"eval_feedback": "pass"}


# ─────────────────────────────────────────────
# 노드 4: 웹 검색 (Web Search)
# ─────────────────────────────────────────────
def web_search(state: CRAGState) -> dict:
    print("\n[웹 검색]")

    if not tavily_client:
        print("  TAVILY_API_KEY 없음 → 웹 검색 스킵")
        return {"web_results": [], "retry_count": state.get("retry_count", 0) + 1}

    try:
        results     = tavily_client.search(query=state["question"], max_results=3)
        web_results = [r["content"] for r in results.get("results", [])]
        print(f"  웹 검색 결과: {len(web_results)}개")
        return {
            "web_results":  web_results,
            "retry_count":  state.get("retry_count", 0) + 1,
            # 웹 결과를 retrieved_context에 추가 (Add context)
            "retrieved_context": state.get("retrieved_context", []),
        }
    except Exception as e:
        print(f"  웹 검색 오류: {e}")
        return {"web_results": [], "retry_count": state.get("retry_count", 0) + 1}


# ─────────────────────────────────────────────
# 엣지: 평가 결과에 따른 분기
# ─────────────────────────────────────────────
def decide_after_eval(
    state: CRAGState,
) -> Literal["pass", "insufficient", "prompt_fix"]:
    feedback     = state.get("eval_feedback", "pass")
    retry_count  = state.get("retry_count", 0)

    # 최대 재시도 초과 → 강제 종료
    if retry_count >= MAX_RETRY:
        print(f"\n[분기] 최대 재시도({MAX_RETRY}회) 초과 → 현재 답변으로 종료")
        return "pass"

    if feedback == "pass":
        print("\n[분기] 평가 통과 → 최종 답변")
        return "pass"
    elif feedback.startswith("insufficient") or "insufficient" in feedback:
        print("\n[분기] 정보 불충분 → 웹 검색 후 Retrieve 재시도")
        return "insufficient"
    else:
        print("\n[분기] 프롬프트 수정 필요 → Generate 재시도")
        return "prompt_fix"


# ─────────────────────────────────────────────
# LangGraph 그래프 구성
# ─────────────────────────────────────────────
def build_crag_graph():
    graph = StateGraph(CRAGState)

    # 노드 등록
    graph.add_node("retrieve",        retrieve)
    graph.add_node("generate",        generate)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("web_search",      web_search)

    # 엣지 연결
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "evaluate_answer")

    # 평가 후 분기
    graph.add_conditional_edges(
        "evaluate_answer",
        decide_after_eval,
        {
            "pass":        END,             # 통과 → 종료
            "insufficient": "web_search",   # 정보 불충분 → 웹 검색
            "prompt_fix":  "generate",      # 프롬프트 수정 → 재생성
        },
    )

    # 웹 검색 → Add context → Retrieve 재시도 (루프)
    graph.add_edge("web_search", "retrieve")

    return graph.compile()
