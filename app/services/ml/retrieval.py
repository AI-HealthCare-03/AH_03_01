"""하이브리드 RAG 검색 — Dense(PGVector) + Sparse(BM25 Kiwi) + RRF.

ChatRAGGraph 의 retrieve 노드가 이 모듈의 `retrieve()` 만 호출하면 된다.
팀원 `ai_worker/rag/hybrid_search.py` 의 로직을 app 컨텍스트로 이식했으며,
Dense 검색은 ChromaDB 가 아니라 PGVector raw SQL(`embedding <=> $1`) 로 수행한다.

구성:
- Dense: OpenAI text-embedding-3-small 로 쿼리 임베딩 → pgvector 코사인 거리 정렬
- Sparse: 부팅 시 RAGDocument 전체를 메모리에 적재 → Kiwi 형태소(NN/VV/VA/SL)
  → BM25Okapi 인덱스. 청크 규모(현재 434개) 가 작아 메모리 부담 미미.
- 병합: RRF k=60. Dense top-2K + Sparse top-2K → 최종 top-K 반환.

source_type 필터:
- "medical" → document_type=GUIDELINE (KDA2025/KSH2022/DYS_GUIDELINE)
- "service" → document_type=OTHER AND source='GUIDE'
- None     → 필터 없음
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from kiwipiepy import Kiwi  # type: ignore[import-untyped]
from openai import AsyncOpenAI
from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
from tortoise import connections

from app.core import config
from app.models.rag import RAGDocument

# ─────────────────────────────────────────────
# 상수 (팀원 baseline 과 동일)
# ─────────────────────────────────────────────
RRF_K = 60
DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 10  # 각 채널에서 가져올 후보 수 (top_k * 2)

SourceType = Literal["medical", "service", "all"]
# RAGDocument.metadata.disease 값과 대응 (인덱싱 시점에 frontmatter.disease 그대로 저장).
# "general" 은 서비스 가이드(GUIDE), 그 외는 진료지침별 질환.
DiseaseLiteral = Literal["diabetes", "hypertension", "dyslipidemia", "general"]


# ─────────────────────────────────────────────
# 결과 타입
# ─────────────────────────────────────────────
@dataclass(slots=True)
class RetrievedChunk:
    """retrieve() 의 단위 결과. ChatRAGGraph 가 그대로 사용한다."""

    document_id: int  # RAGDocument.id
    source: str  # 예: "KDA2025"
    title: str | None  # 섹션 제목
    chunk_index: int
    chunk_text: str
    document_type: str  # GUIDELINE / OTHER / ...
    metadata: dict[str, Any]
    dense_rank: int | None = None
    sparse_rank: int | None = None
    rrf_score: float = 0.0
    dense_similarity: float | None = None  # 코사인 유사도 (1 - 거리)


# ─────────────────────────────────────────────
# 형태소 분석 (한국어 BM25)
# ─────────────────────────────────────────────
_kiwi: Kiwi | None = None


def _get_kiwi() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        _kiwi = Kiwi()
    return _kiwi


def _tokenize(text: str) -> list[str]:
    """팀원과 동일: 명사(NN)/동사(VV)/형용사(VA)/외래어(SL) 만 추출."""
    tokens = [t.form for t in _get_kiwi().tokenize(text) if t.tag.startswith(("NN", "VV", "VA", "SL"))]
    return tokens if tokens else text.split()


# ─────────────────────────────────────────────
# BM25 인덱스 (프로세스 상주, lazy init)
# ─────────────────────────────────────────────
@dataclass(slots=True)
class _BM25Index:
    bm25: BM25Okapi
    chunk_ids: list[int]  # RAGDocument.id 와 1:1 대응 (BM25 corpus 순서 기준)
    document_types: list[str]
    sources: list[str]
    diseases: list[str | None]  # metadata.disease ("diabetes" | "hypertension" | "dyslipidemia" | "general" | None)
    topics: list[list[str]]  # metadata.topics (["diagnosis", "medication", ...] | [])
    use_restrictions: list[str | None]  # metadata.use_restriction ("included_for_rag" | "pediatric_only" | None)


_bm25_index: _BM25Index | None = None
_bm25_lock = asyncio.Lock()


async def _build_bm25_index() -> _BM25Index:
    """RAGDocument 전체를 로드해 BM25 corpus 를 구축한다.

    문서가 추가/수정될 때마다 재구축이 필요하지만, 인덱싱 빈도가 낮아 부팅 시
    1회 구축으로 충분. 재구축이 필요하면 `invalidate_bm25_index()` 호출.
    """
    rows = await RAGDocument.filter(is_active=True).order_by("id").all()
    corpus: list[list[str]] = []
    chunk_ids: list[int] = []
    document_types: list[str] = []
    sources: list[str] = []
    diseases: list[str | None] = []
    topics: list[list[str]] = []
    use_restrictions: list[str | None] = []
    for r in rows:
        corpus.append(_tokenize(r.chunk_text))
        chunk_ids.append(r.id)
        document_types.append(str(r.document_type))
        sources.append(r.source)
        diseases.append((r.metadata or {}).get("disease"))
        topics.append((r.metadata or {}).get("topics") or [])
        use_restrictions.append((r.metadata or {}).get("use_restriction"))

    if not corpus:
        # 빈 corpus 인 경우 BM25Okapi 가 ZeroDivision 을 던지므로 더미 문서 1개 추가
        corpus = [["__empty__"]]
        chunk_ids = [-1]
        document_types = [""]
        sources = [""]
        diseases = [None]
        topics = [[]]
        use_restrictions = [None]

    return _BM25Index(
        bm25=BM25Okapi(corpus),
        chunk_ids=chunk_ids,
        document_types=document_types,
        sources=sources,
        diseases=diseases,
        topics=topics,
        use_restrictions=use_restrictions,
    )


async def _get_bm25_index() -> _BM25Index:
    global _bm25_index
    if _bm25_index is not None:
        return _bm25_index
    async with _bm25_lock:
        if _bm25_index is None:
            _bm25_index = await _build_bm25_index()
    return _bm25_index


def invalidate_bm25_index() -> None:
    """RAGDocument 재인덱싱 후 BM25 corpus 를 갱신하려면 호출."""
    global _bm25_index
    _bm25_index = None


# ─────────────────────────────────────────────
# 임베딩 (쿼리 1건, async)
# ─────────────────────────────────────────────
_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 가 비어 있어 RAG 검색을 수행할 수 없습니다.")
        # 임베딩 호출도 동일 타임아웃/리트라이 정책 적용 (ChatRAGGraph 와 일관).
        _openai_client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.OPENAI_REQUEST_TIMEOUT,
            max_retries=config.OPENAI_MAX_RETRIES,
        )
    return _openai_client


async def _embed_query(query: str) -> list[float]:
    client = _get_openai_client()
    resp = await client.embeddings.create(model=config.OPENAI_EMBEDDING_MODEL, input=[query])
    return list(resp.data[0].embedding)


# ─────────────────────────────────────────────
# Dense 검색 (pgvector raw SQL)
# ─────────────────────────────────────────────
SERVICE_SOURCES: tuple[str, ...] = ("GUIDE", "CHALLENGE_CATALOG")


def _build_filter_sql(
    source_type: SourceType,
    diseases: list[str] | None,
    topics: list[str] | None = None,
) -> tuple[str, list[Any]]:
    """source_type + disease + topic 필터에 해당하는 WHERE 절 추가분 + bind 인자.

    바인드 인자 인덱스는 $2 부터 사용 (호출 측에서 $1 은 쿼리 임베딩).
    source_type="service" 일 때는 GUIDE/CHALLENGE_CATALOG 둘 다 매치하고 disease/topic 필터를
    무시한다 (서비스 가이드·챌린지 카탈로그는 질환 횡단 자료).
    diseases 는 list — 1개면 단일 질환, 2개 이상이면 OR 매치 (multi-disease 라우팅).
    topics 는 list — metadata.topics jsonb 배열과 ?| 연산자로 OR 매치.
    """
    clauses: list[str] = []
    args: list[Any] = []
    next_idx = 2

    if source_type == "medical":
        clauses.append(f' AND "document_type" = ${next_idx} ')
        args.append("GUIDELINE")
        next_idx += 1
    elif source_type == "service":
        doc_type_idx = next_idx
        args.append("OTHER")
        next_idx += 1
        source_placeholders = ", ".join(f"${next_idx + i}" for i in range(len(SERVICE_SOURCES)))
        clauses.append(f' AND "document_type" = ${doc_type_idx} AND "source" IN ({source_placeholders}) ')
        args.extend(SERVICE_SOURCES)
        next_idx += len(SERVICE_SOURCES)
        # service 카테고리는 disease 필터 비활성 (질환 횡단)
        return ("".join(clauses), args)

    if diseases and source_type == "medical":
        # medical(GUIDELINE) 전용 필터. source_type="all" 이면 CHALLENGE_CATALOG(disease=chronic_disease)가
        # 걸러지므로 의도적으로 비활성.
        disease_placeholders = ", ".join(f"${next_idx + i}" for i in range(len(diseases)))
        clauses.append(f" AND (\"metadata\" ->> 'disease') IN ({disease_placeholders}) ")
        args.extend(diseases)
        next_idx += len(diseases)

    if topics and source_type != "service":
        # metadata.topics 는 jsonb 배열. ?| 연산자로 topics 중 하나라도 포함된 청크 매치.
        # 예: ["diagnosis", "medication"] → metadata->'topics' ?| ARRAY['diagnosis','medication']
        topic_placeholders = ", ".join(f"${next_idx + i}" for i in range(len(topics)))
        clauses.append(f" AND (\"metadata\" -> 'topics') ?| ARRAY[{topic_placeholders}] ")
        args.extend(topics)
        next_idx += len(topics)

    return ("".join(clauses), args)


def _build_pediatric_exclusion_sql(next_idx: int) -> tuple[str, list[Any]]:
    """소아 전용 섹션(use_restriction=pediatric_only)을 검색에서 제외하는 WHERE 절.

    include_pediatric=False(기본)일 때 호출. pediatric_only 섹션은 성인 질문에서
    오검색되어 Faithfulness를 낮추므로 기본적으로 제외한다.
    """
    clause = f" AND (\"metadata\" ->> 'use_restriction') IS DISTINCT FROM ${next_idx} "
    return clause, ["pediatric_only"]


async def _dense_search(
    query_embedding: list[float],
    top_k: int,
    source_type: SourceType,
    diseases: list[str] | None,
    topics: list[str] | None = None,
    ped_clause: str = "",
    ped_args: list[Any] | None = None,
) -> list[tuple[int, float]]:
    """(document_id, cosine_similarity) 튜플 리스트, 유사도 내림차순."""
    filter_sql, filter_args = _build_filter_sql(source_type, diseases, topics)
    # pediatric 제외 절 추가 (include_pediatric=False일 때)
    if ped_clause:
        # ped_args의 바인드 인덱스를 기존 args 뒤로 조정
        adjusted_ped_clause = ped_clause.replace("$2", f"${len(filter_args) + 2}")
        filter_sql += adjusted_ped_clause
        filter_args += ped_args or []
    # asyncpg 는 vector 컬럼 코덱 등록되어 있어 list[float] 그대로 전달 가능 (databases.py 의 init).
    sql = f"""
        SELECT "id", 1 - ("embedding" <=> $1) AS similarity
        FROM "rag_documents"
        WHERE "is_active" = TRUE AND "embedding" IS NOT NULL
        {filter_sql}
        ORDER BY "embedding" <=> $1 ASC
        LIMIT {int(top_k)}
    """
    conn = connections.get("default")
    _, rows = await conn.execute_query(sql, [query_embedding, *filter_args])
    return [(int(r["id"]), float(r["similarity"])) for r in rows]


# ─────────────────────────────────────────────
# Sparse 검색 (BM25)
# ─────────────────────────────────────────────
def _sparse_search(  # noqa: C901
    bm: _BM25Index,
    query: str,
    top_k: int,
    source_type: SourceType,
    diseases: list[str] | None,
    topics: list[str] | None = None,
    ped_clause: str = "",
    ped_args: list[Any] | None = None,
) -> list[tuple[int, float]]:
    """BM25 점수 기준 상위 top_k (document_id, score).

    source_type="service" 는 GUIDE/CHALLENGE_CATALOG 둘 다 통과시키고 disease/topic 필터를
    무시한다 (질환 횡단). _build_filter_sql 과 동일 정책. diseases 가 list 면 OR 매치.
    topics 가 list 면 OR 매치 — 청크의 topics 중 하나라도 포함되면 통과.
    """
    tokens = _tokenize(query)
    scores = bm.bm25.get_scores(tokens)

    # 필터 미통과 항목은 -inf 로 마스킹 (BM25 정상 음수 점수와 구분).
    mask_value = float("-inf")

    if source_type != "all":
        for i, dt in enumerate(bm.document_types):
            if source_type == "medical" and dt != "GUIDELINE":
                scores[i] = mask_value
            elif source_type == "service" and not (dt == "OTHER" and bm.sources[i] in SERVICE_SOURCES):
                scores[i] = mask_value

    # disease 필터 (medical 전용 — service/all 은 횡단). list 면 OR 매치.
    if diseases and source_type == "medical":
        disease_set = set(diseases)
        for i, d in enumerate(bm.diseases):
            if d not in disease_set:
                scores[i] = mask_value

    # topic 필터 (medical/all 케이스에만 — service 는 횡단). list 면 OR 매치.
    # topics=[] 인 청크(매핑 누락)는 필터 통과시켜 검색 누락 방지.
    if topics and source_type != "service":
        topic_set = set(topics)
        for i, chunk_topics in enumerate(bm.topics):
            if chunk_topics and not topic_set.intersection(chunk_topics):
                scores[i] = mask_value

    # pediatric_only 섹션 제외 (include_pediatric=False일 때 ped_args=["pediatric_only"])
    if ped_args and source_type != "service":
        for i, use_restr in enumerate(bm.use_restrictions):
            if use_restr in ped_args:
                scores[i] = mask_value

    # 마스크되지 않은 점수만 상위 top_k. BM25 음수 점수도 정상 결과로 인정 (corpus
    # 작을 때 IDF 음수 케이스). 점수 0 미만 정상값을 필요할 때 살리기 위함.
    indexed = [(i, float(s)) for i, s in enumerate(scores) if s != mask_value]
    indexed.sort(key=lambda x: x[1], reverse=True)
    # 상위 top_k 중 0보다 큰 점수만 의미 있는 결과로 반환 (마스크는 이미 제거됨).
    return [(bm.chunk_ids[i], s) for i, s in indexed[:top_k] if s > 0]


# ─────────────────────────────────────────────
# RRF 병합
# ─────────────────────────────────────────────
def _rrf_merge(
    dense: list[tuple[int, float]],
    sparse: list[tuple[int, float]],
    top_k: int,
    k: int = RRF_K,
) -> dict[int, dict[str, Any]]:
    """document_id → {rrf_score, dense_rank, sparse_rank, dense_similarity} 매핑.
    상위 top_k 만 반환 (rrf_score 내림차순).
    """
    merged: dict[int, dict[str, Any]] = {}

    for rank, (doc_id, sim) in enumerate(dense):
        merged.setdefault(doc_id, {"rrf_score": 0.0, "dense_rank": None, "sparse_rank": None, "dense_similarity": None})
        merged[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)
        merged[doc_id]["dense_rank"] = rank + 1
        merged[doc_id]["dense_similarity"] = sim

    for rank, (doc_id, _) in enumerate(sparse):
        merged.setdefault(doc_id, {"rrf_score": 0.0, "dense_rank": None, "sparse_rank": None, "dense_similarity": None})
        merged[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)
        merged[doc_id]["sparse_rank"] = rank + 1

    # 상위 top_k 만
    sorted_ids = sorted(merged.keys(), key=lambda d: merged[d]["rrf_score"], reverse=True)[:top_k]
    return {d: merged[d] for d in sorted_ids}


# ─────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────
@dataclass(slots=True)
class RetrievalDebug:
    """디버깅/로깅용 검색 메트릭. retrieve() 호출자가 필요 시 참조."""

    query: str
    source_type: SourceType
    diseases: list[str] | None = None
    dense_hits: int = 0
    sparse_hits: int = 0
    merged_returned: int = 0
    dense_top_id: int | None = None
    sparse_top_id: int | None = None


@dataclass(slots=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    debug: RetrievalDebug = field(default_factory=lambda: RetrievalDebug(query="", source_type="all"))


async def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    source_type: SourceType = "all",
    disease: str | list[str] | None = None,
    topics: list[str] | None = None,
    include_pediatric: bool = False,
) -> RetrievalResult:
    """하이브리드 검색.

    Args:
        query: 검색 쿼리 (사용자 질문 또는 그래프가 재작성한 쿼리)
        top_k: 최종 반환 청크 수
        candidate_k: 각 채널(Dense/Sparse) 에서 가져올 후보 수. RRF 안정성을 위해
            보통 top_k 의 2배 이상.
        source_type: "medical" (의료 진료지침) / "service" (서비스 가이드) / "all"
        disease: classify_intent 가 분류한 질환. 단일 문자열 또는 list (multi-disease).
            "diabetes" / "hypertension" / "dyslipidemia" / "general" / None / list.
            None / "general" / 빈 리스트 는 필터 없음.
        topics: classify_intent 가 추출한 topic 목록. ["diagnosis", "medication", ...].
            None 이면 topic 필터 없음. topics=[] 인 청크는 필터 통과 (매핑 누락 안전망).

    Returns:
        RetrievalResult — chunks (rrf_score 내림차순) + debug 메트릭
    """
    # 정규화: 단일 문자열은 list 로 wrap, "general" 은 필터 없음.
    if disease is None:
        diseases: list[str] | None = None
    elif isinstance(disease, str):
        diseases = None if disease == "general" else [disease]
    else:
        diseases = [d for d in disease if d and d != "general"] or None

    debug = RetrievalDebug(query=query, source_type=source_type, diseases=diseases)

    if not query.strip():
        return RetrievalResult(chunks=[], debug=debug)

    # 1) Dense + Sparse 후보 수집
    query_emb = await _embed_query(query)
    bm = await _get_bm25_index()

    # include_pediatric=False(기본)이면 소아 전용 섹션을 검색풀에서 제외.
    # is_pediatric 질문(소아·어린이·청소년 키워드)일 때만 True로 전달.
    if not include_pediatric and source_type != "service":
        ped_clause, ped_args = _build_pediatric_exclusion_sql(2)
    else:
        ped_clause, ped_args = "", []

    dense = await _dense_search(
        query_emb, candidate_k, source_type, diseases, topics, ped_clause=ped_clause, ped_args=ped_args
    )
    sparse = _sparse_search(
        bm, query, candidate_k, source_type, diseases, topics, ped_clause=ped_clause, ped_args=ped_args
    )

    # Topic 필터 soft fallback: topic 필터 적용 후 결과가 없으면 topic 없이 재검색.
    # KB 섹션의 topic 태그가 질문 감지 topic과 불일치할 때 검색 공백 방지.
    if topics and not dense and not sparse:
        dense = await _dense_search(
            query_emb, candidate_k, source_type, diseases, None, ped_clause=ped_clause, ped_args=ped_args
        )
        sparse = _sparse_search(
            bm, query, candidate_k, source_type, diseases, None, ped_clause=ped_clause, ped_args=ped_args
        )

    debug.dense_hits = len(dense)
    debug.sparse_hits = len(sparse)
    debug.dense_top_id = dense[0][0] if dense else None
    debug.sparse_top_id = sparse[0][0] if sparse else None

    if not dense and not sparse:
        return RetrievalResult(chunks=[], debug=debug)

    # 2) RRF 병합
    merged = _rrf_merge(dense, sparse, top_k)
    if not merged:
        return RetrievalResult(chunks=[], debug=debug)

    # 3) RAGDocument 메타·본문 일괄 로드 (병합 결과 id 만)
    doc_rows = await RAGDocument.filter(id__in=list(merged.keys())).all()
    docs_by_id = {d.id: d for d in doc_rows}

    # 4) RetrievedChunk 조립 (RRF 점수 순서 유지)
    out: list[RetrievedChunk] = []
    for doc_id in merged:
        doc = docs_by_id.get(doc_id)
        if doc is None:
            continue  # rare: 검색과 fetch 사이 삭제된 경우
        info = merged[doc_id]
        out.append(
            RetrievedChunk(
                document_id=doc.id,
                source=doc.source,
                title=doc.title,
                chunk_index=doc.chunk_index,
                chunk_text=doc.chunk_text,
                document_type=str(doc.document_type),
                metadata=dict(doc.metadata or {}),
                dense_rank=info["dense_rank"],
                sparse_rank=info["sparse_rank"],
                rrf_score=info["rrf_score"],
                dense_similarity=info["dense_similarity"],
            )
        )

    debug.merged_returned = len(out)
    return RetrievalResult(chunks=out, debug=debug)
