from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """risk_recommendation_results — RAG 위험도 권고 그래프 결과 이력 (append-only).

    서빙 캐시는 Redis 단기 캐시가 담당하고, 본 테이블은 추이/통계/백업용 append-only
    이력(사용자당 다수 row)이다. 그래프가 저장 가드를 통과할 때마다 한 행을 insert 한다.
    (user_id, created_at) 인덱스로 최신본·추이 조회를 가속한다.
    """
    return """
        CREATE TABLE IF NOT EXISTS "risk_recommendation_results" (
            "id"                  BIGSERIAL PRIMARY KEY,
            "user_id"             UUID NOT NULL
                                      REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
            "input_snapshot"      JSONB NOT NULL DEFAULT '{}',
            "model_version"       VARCHAR(40) NOT NULL DEFAULT 'risk-graph-v1',
            "answer"              TEXT NOT NULL DEFAULT '',
            "tips"                JSONB NOT NULL DEFAULT '[]',
            "diet"                JSONB NOT NULL DEFAULT '[]',
            "sources"             JSONB NOT NULL DEFAULT '[]',
            "predictions"         JSONB NOT NULL DEFAULT '[]',
            "is_fallback"         BOOL NOT NULL DEFAULT FALSE,
            "eval_revision_count" INT,
            "created_at"          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_risk_rec_user_created"
            ON "risk_recommendation_results" ("user_id", "created_at" DESC);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "risk_recommendation_results";
    """
