"""
Chroma 검색 테스트
======================================
"""

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import OpenAI

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE = Path(__file__).parent
CHROMA_DIR = BASE / "chroma_db"

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chronic_disease_rag"
TOP_K = 5  # 상위 몇 개 청크 가져올지

# ─────────────────────────────────────────────
# 테스트 쿼리 목록
# ─────────────────────────────────────────────
TEST_QUERIES = [
    "당뇨병 혈당 목표 수치가 어떻게 돼?",
    "고혈압 환자 혈압 정상 기준",
    "당뇨병 운동요법 권고사항",
    "챌린지 인증 실패하면 어떻게 해?",
    "이상지질혈증 LDL 콜레스테롤 치료 목표",
]


# ─────────────────────────────────────────────
# 클라이언트 초기화
# ─────────────────────────────────────────────
def init_clients():
    # .env 로드
    env_path = BASE.parent.parent / "envs" / ".local.env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 없음. .env 파일 확인하세요.")

    openai_client = OpenAI(api_key=api_key)
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return openai_client, chroma_client


def get_embedding(client: OpenAI, text: str) -> list[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
    )
    return response.data[0].embedding


# ─────────────────────────────────────────────
# 검색 테스트
# ─────────────────────────────────────────────
def search(collection, openai_client, query: str, top_k: int = TOP_K):
    embedding = get_embedding(openai_client, query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return results


def print_results(query: str, results: dict):
    print(f"\n{'=' * 60}")
    print(f"  🔍 쿼리: {query}")
    print(f"{'=' * 60}")

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances, strict=False)):
        similarity = 1 - dist  # 코사인 거리 → 유사도
        print(f"\n  [{i + 1}위] 유사도: {similarity:.4f}")
        print(f"  출처: {meta.get('source_id', '?')} | {meta.get('section_title', '?')}")
        print(f"  파일: {meta.get('file', '?')} | 페이지: {meta.get('source_pages', '?')}")
        print(f"  내용: {doc[:150]}{'...' if len(doc) > 150 else ''}")
        print(f"  {'─' * 55}")


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Chroma 검색 테스트")
    print("=" * 60)

    if not CHROMA_DIR.exists():
        raise FileNotFoundError("chroma_db/ 없음. chroma_loader.py 먼저 실행하세요.")

    openai_client, chroma_client = init_clients()
    collection = chroma_client.get_collection(name=COLLECTION_NAME)

    print(f"\n  컬렉션 총 청크 수: {collection.count()}개")
    print(f"  TOP_K: {TOP_K}개\n")

    for query in TEST_QUERIES:
        results = search(collection, openai_client, query)
        print_results(query, results)

    print(f"\n{'=' * 60}")
    print("  ✅ 테스트 완료!")
    print("=" * 60)
