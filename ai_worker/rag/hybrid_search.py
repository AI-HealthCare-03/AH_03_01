"""
BM25 + Hybrid 검색 (Dense + Sparse)
======================================

설치 :
pip install rank_bm25 kiwipiepy chromadb openai

구조:
    Dense  검색: Chroma 벡터 유사도 검색
    Sparse 검색: BM25 키워드 검색 (한국어 형태소 분석 with Kiwi)
    Hybrid 검색: 두 결과를 RRF(Reciprocal Rank Fusion)로 병합
"""

import os
import json
import math
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from rank_bm25 import BM25Okapi
from kiwipiepy import Kiwi

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE        = Path(__file__).parent
CHROMA_DIR  = BASE / "chroma_db"
CHUNKS_PATH = BASE / "output" / "chunks.json"

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chronic_disease_rag"
TOP_K           = 5    # 최종 반환 청크 수
RRF_K           = 60   # RRF 상수 (보통 60 고정)

# ─────────────────────────────────────────────
# 테스트 쿼리
# ─────────────────────────────────────────────
TEST_QUERIES = [
    "당뇨병 혈당 목표 수치가 어떻게 돼?",
    "고혈압 환자 혈압 정상 기준",
    "당뇨병 운동요법 권고사항",
    "챌린지 인증 실패하면 어떻게 해?",
    "이상지질혈증 LDL 콜레스테롤 치료 목표",
]

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
# 한국어 형태소 분석 (Kiwi)
# ─────────────────────────────────────────────
kiwi = Kiwi()

def tokenize(text: str) -> list[str]:
    """한국어 텍스트를 형태소 단위로 분리"""
    tokens = []
    for token in kiwi.tokenize(text):
        # 명사(NN), 동사(VV), 형용사(VA), 영어(SL) 만 사용
        if token.tag.startswith(("NN", "VV", "VA", "SL")):
            tokens.append(token.form)
    return tokens if tokens else text.split()


# ─────────────────────────────────────────────
# BM25 인덱스 구축
# ─────────────────────────────────────────────
def build_bm25_index(chunks: list[dict]):
    print("  BM25 인덱스 구축 중 (형태소 분석)...")
    tokenized_corpus = [tokenize(c["content"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    print(f"  BM25 인덱스 완료: {len(chunks)}개 청크")
    return bm25, tokenized_corpus


# ─────────────────────────────────────────────
# Dense 검색 (Chroma 벡터)
# ─────────────────────────────────────────────
def dense_search(
    collection,
    openai_client: OpenAI,
    query: str,
    top_k: int,
) -> list[dict]:
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
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
    ):
        output.append({
            "content":  doc,
            "metadata": meta,
            "score":    1 - dist,  # 코사인 거리 → 유사도
        })
    return output


# ─────────────────────────────────────────────
# Sparse 검색 (BM25)
# ─────────────────────────────────────────────
def sparse_search(
    bm25: BM25Okapi,
    chunks: list[dict],
    query: str,
    top_k: int,
) -> list[dict]:
    query_tokens = tokenize(query)
    scores       = bm25.get_scores(query_tokens)

    # 상위 top_k 인덱스 추출
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    output = []
    for idx in top_indices:
        output.append({
            "content":  chunks[idx]["content"],
            "metadata": {k: v for k, v in chunks[idx].items() if k != "content"},
            "score":    float(scores[idx]),
            "index":    idx,
        })
    return output


# ─────────────────────────────────────────────
# RRF (Reciprocal Rank Fusion) 병합
# ─────────────────────────────────────────────
def rrf_merge(
    dense_results:  list[dict],
    sparse_results: list[dict],
    top_k: int,
    k: int = RRF_K,
) -> list[dict]:
    """
    두 검색 결과를 RRF로 병합
    RRF score = 1/(k + rank_dense) + 1/(k + rank_sparse)
    """
    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}

    # Dense 결과에 RRF 점수 부여
    for rank, item in enumerate(dense_results):
        key = item["content"][:100]  # 내용 앞 100자를 키로 사용
        rrf_scores[key]  = rrf_scores.get(key, 0) + 1 / (k + rank + 1)
        content_map[key] = item

    # Sparse 결과에 RRF 점수 부여
    for rank, item in enumerate(sparse_results):
        key = item["content"][:100]
        rrf_scores[key]  = rrf_scores.get(key, 0) + 1 / (k + rank + 1)
        if key not in content_map:
            content_map[key] = item

    # RRF 점수 기준 정렬
    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

    output = []
    for key in sorted_keys[:top_k]:
        item = content_map[key].copy()
        item["rrf_score"] = rrf_scores[key]
        output.append(item)
    return output


# ─────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────
def print_results(query: str, results: list[dict], mode: str = "Hybrid"):
    print(f"\n{'=' * 60}")
    print(f"  🔍 [{mode}] 쿼리: {query}")
    print(f"{'=' * 60}")

    for i, item in enumerate(results):
        meta      = item.get("metadata", {})
        rrf_score = item.get("rrf_score", item.get("score", 0))
        print(f"\n  [{i+1}위] RRF점수: {rrf_score:.4f}")
        print(f"  출처: {meta.get('source_id', '?')} | {meta.get('section_title', '?')}")
        print(f"  파일: {meta.get('file', '?')} | 페이지: {meta.get('source_pages', '?')}")
        print(f"  내용: {item['content'][:150]}{'...' if len(item['content']) > 150 else ''}")
        print(f"  {'─' * 55}")


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  BM25 + Hybrid 검색 테스트")
    print("=" * 60)

    # 클라이언트 초기화
    openai_client, chroma_client = init_clients()
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    print(f"\n  컬렉션 총 청크 수: {collection.count()}개")

    # chunks.json 로드 (BM25용)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    # BM25 인덱스 구축
    bm25, _ = build_bm25_index(chunks)

    print(f"\n  검색 시작 (TOP_K={TOP_K})\n")

    for query in TEST_QUERIES:
        # Dense 검색
        dense_results  = dense_search(collection, openai_client, query, top_k=TOP_K * 2)
        # Sparse 검색
        sparse_results = sparse_search(bm25, chunks, query, top_k=TOP_K * 2)
        # Hybrid 병합
        hybrid_results = rrf_merge(dense_results, sparse_results, top_k=TOP_K)

        print_results(query, hybrid_results)

    print(f"\n{'=' * 60}")
    print("  ✅ Hybrid 검색 테스트 완료!")
    print("=" * 60)
