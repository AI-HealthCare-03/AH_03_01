from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """RAGDocument.embedding 차원 768 → 1536 (OpenAI text-embedding-3-small).

    팀원 RAG 프로토타입과 동일한 임베딩 모델을 ChatRAGGraph 통합에 사용하기 위해
    PGVector 컬럼 차원을 1536 으로 확장한다. ALTER 시 `USING NULL` 캐스트로
    기존 임베딩은 NULL 화되므로, 잔여 임베딩이 있는 환경(dev/staging)에서는
    데이터 손실을 막기 위해 사전 가드로 차단한다.
    """
    rows = await db.execute_query_dict('SELECT count(*) AS c FROM "rag_documents" WHERE "embedding" IS NOT NULL')
    existing = int(rows[0]["c"]) if rows else 0
    if existing > 0:
        raise RuntimeError(
            f"rag_documents 에 임베딩 {existing}행이 남아 있어 차원 변경을 거부합니다. "
            "수동으로 백업/삭제 (또는 768d 모델로 다시 사용) 후 다시 실행하세요."
        )
    return """
        ALTER TABLE "rag_documents"
        ALTER COLUMN "embedding" TYPE vector(1536) USING NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    # downgrade 도 동일하게 잔여 임베딩 차단 (역방향에서도 데이터 손실 방지).
    rows = await db.execute_query_dict('SELECT count(*) AS c FROM "rag_documents" WHERE "embedding" IS NOT NULL')
    existing = int(rows[0]["c"]) if rows else 0
    if existing > 0:
        raise RuntimeError(f"rag_documents 에 임베딩 {existing}행이 남아 있어 차원 변경을 거부합니다.")
    return """
        ALTER TABLE "rag_documents"
        ALTER COLUMN "embedding" TYPE vector(768) USING NULL;
    """
