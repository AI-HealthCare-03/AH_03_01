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
    Retrieve  (Hybrid 검색 + 소스 유형 사전 필터링)
      ↓
    GradeDocuments  (관련성 배치 평가, 간접 관련도 포함)
      ├→ 충분 → Generate → Evaluator
      │                    ├→ Pass          → Answer
      │                    ├→ 정보 불충분    → WebSearch → Retrieve
      │                    └→ 프롬프트 수정  → Generate 재시도
      ├→ 부족 + rewrite_count < 2 → RewriteQuery → Retrieve
      └→ 부족 + rewrite_count ≥ 2 → WebSearch → Retrieve
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

EMBEDDING_MODEL    = "text-embedding-3-small"
LLM_MODEL          = "gpt-4o-mini"
COLLECTION_NAME    = "chronic_disease_rag"
TOP_K              = 5
RRF_K              = 60
MAX_RETRY          = 2   # 평가 후 재시도 최대 횟수
MAX_REWRITE        = 2   # 쿼리 재작성 최대 횟수
MAX_SECTION_CHUNKS = 3   # 같은 section_id에서 최대 허용 청크 수 (기존 1 → 3)
MIN_RELEVANT_DOCS  = 1   # grade 통과 후 generate로 가기 위한 최소 문서 수

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

# 스트리밍 LLM: generate 노드 전용
llm = ChatOpenAI(model=LLM_MODEL, temperature=0, streaming=True)

# 경량 LLM: grade / rewrite / evaluate 노드 전용 (비용 절감, 스트리밍 불필요)
eval_llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

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
# 소스 유형 감지 (질문 유형 → 검색 소스 분리)
# ─────────────────────────────────────────────
# 서비스 관련 키워드 (GUIDE 소스 우선 검색)
_SERVICE_KW = frozenset(["챌린지", "포인트", "인증", "아이템", "상점", "실패 방지권", "챌린저"])
# 의료 관련 키워드 (GUIDE 소스 제외)
_MEDICAL_KW = frozenset([
    "혈압", "혈당", "당뇨", "고혈압", "콜레스테롤", "LDL", "HDL",
    "인슐린", "이상지질", "심혈관", "당화혈색소", "스타틴", "메트포르민",
    "합병증", "진단", "치료", "약",
])

def detect_source_type(question: str) -> str:
    """
    질문 내 키워드 기반으로 검색 소스 유형 판별
    Returns: 'service' | 'medical' | 'all'
    """
    for kw in _SERVICE_KW:
        if kw in question:
            return "service"
    for kw in _MEDICAL_KW:
        if kw in question:
            return "medical"
    return "all"


# ─────────────────────────────────────────────
# Hybrid 검색 (소스 필터링 지원)
# ─────────────────────────────────────────────
def hybrid_search(
    query: str,
    top_k: int = TOP_K,
    source_type: str = "all",
) -> list[dict]:
    """
    Dense(ChromaDB) + Sparse(BM25) Hybrid 검색
    source_type: 'service' → GUIDE만 / 'medical' → GUIDE 제외 / 'all' → 전체
    """
    # ── Dense 검색 (ChromaDB, 소스 필터 적용) ──
    emb = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])

    chroma_kwargs: dict = dict(
        query_embeddings=[emb.data[0].embedding],
        n_results=min(top_k * 2, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    if source_type == "service":
        chroma_kwargs["where"] = {"source_id": "GUIDE"}
    elif source_type == "medical":
        chroma_kwargs["where"] = {"source_id": {"$ne": "GUIDE"}}

    results = collection.query(**chroma_kwargs)
    dense = [
        {"content": d, "metadata": m, "score": 1 - s}
        for d, m, s in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]

    # ── Sparse 검색 (BM25, 소스 필터 후처리) ──
    scores  = bm25.get_scores(tokenize(query))
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    # source_type에 따라 BM25 결과 후처리 필터링
    if source_type != "all":
        filtered_idx = []
        for i in top_idx:
            sid = chunks[i].get("source_id", "")
            if source_type == "service" and sid == "GUIDE":
                filtered_idx.append(i)
            elif source_type == "medical" and sid != "GUIDE":
                filtered_idx.append(i)
        top_idx = filtered_idx
    top_idx = top_idx[: top_k * 2]

    sparse = [
        {
            "content":  chunks[i]["content"],
            "metadata": {k: v for k, v in chunks[i].items() if k != "content"},
            "score":    float(scores[i]),
        }
        for i in top_idx
    ]

    # ── RRF 병합 ──
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
    question:             str            # 현재 검색 쿼리 (재작성 가능)
    original_question:    str            # 원래 질문 (재작성 후에도 보존, 최종 답변에 사용)
    prediction_result:    Optional[dict] # ML 예측 결과
    retrieved_context:    list[dict]     # 검색된 청크
    web_results:          list[str]      # 웹 검색 결과
    final_recommendation: str            # 최종 답변
    eval_verdict:         str            # 평가 판정: 'pass' | 'insufficient' | 'prompt_fix'
    eval_feedback:        str            # 평가자 피드백 (generate 재시도 시 프롬프트에 반영)
    retry_count:          int            # 평가 재시도 횟수
    rewrite_count:        int            # 쿼리 재작성 횟수


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

    # ML 고위험 질환 쿼리 보강
    if prediction:
        high_risk = [
            DISEASE_KO.get(d, d)
            for d, r in prediction.items()
            if isinstance(r, (int, float)) and r >= 50
        ]
        query = f"{question} {' '.join(high_risk)} 위험군 관련" if high_risk else question
    else:
        query = question

    # 소스 유형 감지 (의료 vs 서비스)
    source_type = detect_source_type(state.get("original_question", question))
    print(f"\n[검색] '{query}' (소스 필터: {source_type})")

    docs = hybrid_search(query, source_type=source_type)

    # ── 개선: section_id 기준 최대 MAX_SECTION_CHUNKS(3)개 허용 ──
    # 기존: section_id 1개만 → 변경: 최대 3개 → Faithfulness 개선
    section_count: dict[str, int] = {}
    unique_docs: list[dict] = []
    for doc in docs:
        section_id = doc.get("metadata", {}).get("section_id", "")
        cnt = section_count.get(section_id, 0)
        if cnt < MAX_SECTION_CHUNKS:
            section_count[section_id] = cnt + 1
            unique_docs.append(doc)
    docs = unique_docs

    print(f"  → {len(docs)}개 청크 검색됨 (section 중복 제어 후)")
    for i, d in enumerate(docs):
        meta = d.get("metadata", {})
        print(f"    [{i+1}] {meta.get('source_id','?')} | {meta.get('section_title','?')}")

    # 기존 컨텍스트(웹 검색 결과 포함) + 새 검색 결과 병합
    existing_context = state.get("retrieved_context", [])
    return {"retrieved_context": existing_context + docs}


# ─────────────────────────────────────────────
# 노드 2: 문서 관련성 평가 (GradeDocuments)
# ─────────────────────────────────────────────
GRADE_PROMPT = """당신은 검색된 문서가 질문과 관련 있는지 평가하는 전문가입니다.

[질문]
{question}

[문서 목록]
{doc_list}

평가 기준:
- 질문과 직접적으로 관련된 내용이면 yes
- 질문과 간접적으로 관련된 내용도 yes (예시: 고혈압 질문에 나트륨 섭취·체중 감량·운동 내용도 yes, 당뇨 질문에 식사요법·운동 내용도 yes)
- 전혀 무관한 내용만 no

각 문서에 대해 반드시 아래 형식으로만 답하세요:
1: yes
2: no
..."""

def grade_documents(state: CRAGState) -> dict:
    """
    검색된 문서 중 질문과 관련 없는 문서 제거 (배치 LLM 호출로 비용 절감)
    """
    docs     = state["retrieved_context"]
    question = state["question"]

    if not docs:
        return {}

    print(f"\n[문서 그레이더] {len(docs)}개 문서 평가 중...")

    doc_list = "\n\n".join([
        f"[{i+1}] {doc['content'][:400]}"
        for i, doc in enumerate(docs)
    ])

    response = eval_llm.invoke([
        HumanMessage(content=GRADE_PROMPT.format(
            question=question,
            doc_list=doc_list,
        ))
    ])

    # 응답 파싱: "번호: yes/no" 형식
    relevant_docs: list[dict] = []
    for line in response.content.strip().splitlines():
        parts = line.split(":", 1)
        if len(parts) == 2:
            try:
                idx     = int(parts[0].strip()) - 1
                verdict = parts[1].strip().lower()
                if 0 <= idx < len(docs) and "yes" in verdict:
                    relevant_docs.append(docs[idx])
            except ValueError:
                continue

    # 파싱 실패 시 전체 문서 유지 (안전장치)
    if not relevant_docs:
        print("  ⚠️ 그레이더 파싱 실패 → 전체 문서 유지")
        relevant_docs = docs

    print(f"  → 관련 문서: {len(relevant_docs)}/{len(docs)}개")
    return {"retrieved_context": relevant_docs}


# ─────────────────────────────────────────────
# 노드 3: 쿼리 재작성 (RewriteQuery)
# ─────────────────────────────────────────────
REWRITE_PROMPT = """검색 결과가 불충분합니다. 더 나은 검색 결과를 얻기 위해 질문을 재작성해주세요.

원래 질문: {question}
재작성 횟수: {rewrite_count}회차

요령:
- 핵심 의도는 유지하면서 의학 용어 또는 다른 표현 사용
- 1회차: 좀 더 구체적으로 / 2회차: 유사어·동의어 활용

재작성된 질문만 출력하세요 (설명 없이)."""

def rewrite_query(state: CRAGState) -> dict:
    """
    관련 문서 부족 시 쿼리 재작성 (최대 MAX_REWRITE회)
    """
    rewrite_count = state.get("rewrite_count", 0)
    response = eval_llm.invoke([
        HumanMessage(content=REWRITE_PROMPT.format(
            question=state["question"],
            rewrite_count=rewrite_count + 1,
        ))
    ])
    new_q = response.content.strip()
    print(f"\n[쿼리 재작성 {rewrite_count + 1}회차]")
    print(f"  이전: {state['question']}")
    print(f"  이후: {new_q}")

    return {
        "question":          new_q,
        "rewrite_count":     rewrite_count + 1,
        "retrieved_context": [],          # 이전 결과 초기화
    }


# ─────────────────────────────────────────────
# 엣지: 그레이드 결과에 따른 분기
# ─────────────────────────────────────────────
def route_after_grade(
    state: CRAGState,
) -> Literal["generate", "rewrite_query", "web_search"]:
    """
    관련 문서가 충분하면 generate, 부족하면 재작성 or 웹 검색
    """
    docs          = state.get("retrieved_context", [])
    rewrite_count = state.get("rewrite_count", 0)
    web_results   = state.get("web_results", [])

    # 웹 검색 결과가 있거나 문서 충분하면 generate 진행
    if len(docs) >= MIN_RELEVANT_DOCS or web_results:
        print("\n[분기] 문서 충분 or 웹 결과 존재 → Generate")
        return "generate"

    # 재작성 가능 횟수 남아 있으면 재작성
    if rewrite_count < MAX_REWRITE:
        print(f"\n[분기] 관련 문서 부족 → 쿼리 재작성 ({rewrite_count + 1}/{MAX_REWRITE}회차)")
        return "rewrite_query"

    # 재작성 한계 → 웹 검색
    print("\n[분기] 재작성 한계 도달 → 웹 검색")
    return "web_search"


# ─────────────────────────────────────────────
# 노드 4: 답변 생성 (Generate)
# ─────────────────────────────────────────────
SYSTEM_PROMPT_MEDICAL = """당신은 만성질환(고혈압·당뇨·이상지질혈증) 생활습관 관리 서비스의 전문 챗봇입니다.

## 답변 규칙
1. 반드시 제공된 [참고 자료]만을 근거로 답변하세요.
2. 참고 자료에 없는 내용은 "제공된 자료에서 확인할 수 없습니다"라고 답하세요.
3. "~할 수 있습니다", "~권고됩니다" 형식으로 답하세요.
4. 한국어로 답변하세요.
5. 복잡한 의학 용어는 쉽게 풀어서 설명하세요.
6. 답변 마지막에 반드시 면책 문구를 포함하세요.

## 면책 문구 (항상 포함)
> ⚠️ 본 답변은 일반적인 건강 정보 제공을 목적으로 하며, 의료적 진단·처방·치료를 대체하지 않습니다. 정확한 진단과 치료는 반드시 의료 전문가에게 문의하세요."""

SYSTEM_PROMPT_SERVICE = """당신은 만성질환 생활습관 관리 서비스의 친절한 안내 챗봇입니다.

## 답변 규칙
1. 반드시 제공된 [참고 자료]만을 근거로 답변하세요.
2. 참고 자료에 없는 내용은 "제공된 자료에서 확인할 수 없습니다"라고 답하세요.
3. 친절하고 명확하게 안내해주세요.
4. 한국어로 답변하세요."""


def classify_question(docs: list[dict]) -> str:
    """검색된 청크의 source_id 기반으로 질문 유형 분류"""
    source_ids  = [d.get("metadata", {}).get("source_id", "") for d in docs]
    guide_count = sum(1 for s in source_ids if s == "GUIDE")
    return "service" if guide_count > len(source_ids) / 2 else "medical"


def generate(state: CRAGState) -> dict:
    print("\n[답변 생성]")

    context_parts: list[str] = []

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

    q_type        = classify_question(state["retrieved_context"])
    system_prompt = SYSTEM_PROMPT_MEDICAL if q_type == "medical" else SYSTEM_PROMPT_SERVICE
    print(f"  질문 유형: {q_type}")

    feedback    = state.get("eval_feedback", "")
    extra_guide = f"\n\n## 추가 지침 (이전 답변 보완)\n{feedback}" if feedback else ""

    # 재작성된 경우 원래 질문으로 답변 생성
    display_question = state.get("original_question") or state["question"]
    user_prompt = (
        f"[참고 자료]\n{context}\n\n---\n\n"
        f"[질문]\n{display_question}\n\n"
        f"위 참고 자료를 바탕으로 질문에 답변해주세요."
    )

    print("\n  🤖 답변:")
    print("  " + "─" * 55)
    full_answer = ""
    for chunk in llm.stream([
        SystemMessage(content=system_prompt + extra_guide),
        HumanMessage(content=user_prompt),
    ]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content
    print("\n  " + "─" * 55)

    return {"final_recommendation": full_answer}


# ─────────────────────────────────────────────
# 노드 5: 답변 품질 평가 (Evaluator)
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

    # eval_llm 사용 (스트리밍 없이 비용 절감)
    response = eval_llm.invoke([
        HumanMessage(content=EVAL_PROMPT.format(
            question=state.get("original_question") or state["question"],
            answer=state["final_recommendation"][:800],
        ))
    ])
    result = response.content.strip().lower()
    print(f"  평가 결과: {result}")

    if result.startswith("insufficient"):
        feedback = result.replace("insufficient:", "").strip()
        return {"eval_verdict": "insufficient", "eval_feedback": feedback, "retry_count": state.get("retry_count", 0) + 1}
    elif result.startswith("prompt_fix"):
        feedback = result.replace("prompt_fix:", "").strip()
        return {"eval_verdict": "prompt_fix", "eval_feedback": feedback, "retry_count": state.get("retry_count", 0) + 1}
    else:
        return {"eval_verdict": "pass", "eval_feedback": "", "retry_count": state.get("retry_count", 0)}


# ─────────────────────────────────────────────
# 노드 6: 웹 검색 (WebSearch)
# ─────────────────────────────────────────────
def web_search(state: CRAGState) -> dict:
    print("\n[웹 검색]")

    # 서비스 질문은 외부 웹에 답 없음 → 웹 검색 스킵
    source_type = detect_source_type(state.get("original_question", state["question"]))
    if source_type == "service":
        print("  서비스 질문 → 웹 검색 스킵 (GUIDE 내부 데이터 부족)")
        return {"web_results": [], "retrieved_context": state.get("retrieved_context", [])}

    if not tavily_client:
        print("  TAVILY_API_KEY 없음 → 웹 검색 스킵")
        return {"web_results": [], "retrieved_context": state.get("retrieved_context", [])}

    # 웹 검색은 원래 질문으로
    query = state.get("original_question") or state["question"]
    try:
        results     = tavily_client.search(query=query, max_results=3)
        web_results = [r["content"] for r in results.get("results", [])]
        print(f"  웹 검색 결과: {len(web_results)}개")
        return {
            "web_results":       web_results,
            "retrieved_context": [],   # retrieve 재시도 시 기존 context 초기화
        }
    except Exception as e:
        print(f"  웹 검색 오류: {e}")
        return {"web_results": [], "retrieved_context": []}


# ─────────────────────────────────────────────
# 엣지: 평가 결과에 따른 분기
# ─────────────────────────────────────────────
def decide_after_eval(
    state: CRAGState,
) -> Literal["pass", "insufficient", "prompt_fix"]:
    verdict     = state.get("eval_verdict", "pass")
    retry_count = state.get("retry_count", 0)

    if retry_count >= MAX_RETRY:
        print(f"\n[분기] 최대 재시도({MAX_RETRY}회) 초과 → 현재 답변으로 종료")
        return "pass"

    if verdict == "pass":
        print("\n[분기] 평가 통과 → 최종 답변")
        return "pass"
    elif verdict == "insufficient":
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
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("rewrite_query",   rewrite_query)
    graph.add_node("generate",        generate)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("web_search",      web_search)

    # 엣지 연결
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade_documents")

    # 그레이드 결과 분기: generate / rewrite / web_search
    graph.add_conditional_edges(
        "grade_documents",
        route_after_grade,
        {
            "generate":      "generate",
            "rewrite_query": "rewrite_query",
            "web_search":    "web_search",
        },
    )

    # 재작성 → retrieve 루프
    graph.add_edge("rewrite_query", "retrieve")

    # 웹 검색 → retrieve 루프
    graph.add_edge("web_search", "retrieve")

    # generate → 평가
    graph.add_edge("generate", "evaluate_answer")

    # 평가 결과 분기
    graph.add_conditional_edges(
        "evaluate_answer",
        decide_after_eval,
        {
            "pass":         END,
            "insufficient": "web_search",
            "prompt_fix":   "generate",
        },
    )

    return graph.compile()