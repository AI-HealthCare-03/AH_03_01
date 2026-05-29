"""
Chroma 벡터DB 적재 파이프라인
======================================
"""

import json
import os
import time
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import OpenAI

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE = Path(__file__).parent
CHUNKS_PATH = BASE / "output" / "chunks.json"
CHROMA_DIR = BASE / "chroma_db"

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chronic_disease_rag"
BATCH_SIZE = 50  # 한 번에 임베딩 요청할 청크 수 (API 제한 고려)
RETRY_DELAY = 5  # 오류 시 재시도 대기 시간 (초)


# ─────────────────────────────────────────────
# 클라이언트 초기화
# ─────────────────────────────────────────────
def init_clients():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

    openai_client = OpenAI(api_key=api_key)
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return openai_client, chroma_client


# ─────────────────────────────────────────────
# 임베딩 생성
# ─────────────────────────────────────────────
def get_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """텍스트 리스트를 임베딩 벡터 리스트로 변환"""
    for attempt in range(3):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"  ⚠️  임베딩 오류 (시도 {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(RETRY_DELAY)
    raise RuntimeError("임베딩 생성 3회 실패")


# ─────────────────────────────────────────────
# 메타데이터 정제 (Chroma는 str/int/float/bool만 허용)
# ─────────────────────────────────────────────
def clean_metadata(meta: dict) -> dict:
    cleaned = {}
    for k, v in meta.items():
        if k == "content":
            continue  # content는 document로 따로 저장
        if isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)  # 나머지는 문자열 변환
    return cleaned


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  Chroma 벡터DB 적재 파이프라인")
    print("=" * 55)

    # .env 파일 로드 (python-dotenv 없이 직접 처리)
    env_path = BASE.parent.parent / "envs" / ".local.env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    # 클라이언트 초기화
    openai_client, chroma_client = init_clients()

    # chunks.json 로드
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"chunks.json 없음: {CHUNKS_PATH}\nrag_chunker.py 먼저 실행하세요.")

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"\n  청크 로드: {len(chunks)}개")

    # Chroma 컬렉션 생성 or 기존 연결
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # 코사인 유사도 사용
    )
    print(f"  컬렉션: '{COLLECTION_NAME}'")

    # 이미 적재된 ID 확인 (중복 방지)
    existing_ids = set(collection.get(include=[])["ids"])
    print(f"  기존 적재 청크: {len(existing_ids)}개")

    # 적재할 청크 필터링
    new_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{chunk.get('section_id', 'SEC')}_{chunk.get('chunk_index', i)}"
        if chunk_id not in existing_ids:
            chunk["_id"] = chunk_id
            new_chunks.append(chunk)

    if not new_chunks:
        print("\n  ✅ 새로 적재할 청크 없음 (이미 최신 상태)")
        exit(0)

    print(f"  새로 적재할 청크: {len(new_chunks)}개")
    print()

    # 배치 단위로 임베딩 & 적재
    total_batches = (len(new_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    total_added = 0

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(new_chunks))
        batch = new_chunks[start:end]

        print(f"  배치 {batch_idx + 1}/{total_batches} ({len(batch)}개) 임베딩 중...")

        texts = [c["content"] for c in batch]
        ids = [c["_id"] for c in batch]
        metadatas = [clean_metadata(c) for c in batch]
        embeddings = get_embeddings(openai_client, texts)

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_added += len(batch)
        print(f"    ✅ {total_added}/{len(new_chunks)}개 완료")

    # 최종 확인
    final_count = collection.count()
    print()
    print("  🎉 적재 완료!")
    print(f"  컬렉션 총 청크 수: {final_count}개")
    print(f"  저장 경로: {CHROMA_DIR}")
    print("=" * 55)
