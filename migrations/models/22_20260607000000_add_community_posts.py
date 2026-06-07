from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "community_posts" (
            "id"         BIGSERIAL PRIMARY KEY,
            "title"      VARCHAR(200) NOT NULL,
            "content"    TEXT NOT NULL,
            "category"   VARCHAR(20) NOT NULL,
            "is_pinned"  BOOLEAN NOT NULL DEFAULT FALSE,
            "view_count" INT NOT NULL DEFAULT 0,
            "author_id"  UUID NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """DROP TABLE IF EXISTS "community_posts";"""
