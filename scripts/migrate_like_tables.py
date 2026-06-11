"""community_post_likes / community_comment_likes 테이블 생성 스크립트.

실행 방법:
    docker exec -i fastapi uv run --no-sync python scripts/migrate_like_tables.py

이미 존재하는 테이블은 건너뜁니다 (멱등 실행 가능).
"""

import asyncio
import os

import asyncpg

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "postgres"),
    port=int(os.getenv("DB_PORT", "5432")),
    user=os.getenv("DB_USER", "ozcoding"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_health"),
)

SQL = """
CREATE TABLE IF NOT EXISTS community_post_likes (
    id          BIGSERIAL PRIMARY KEY,
    post_id     BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    user_id     UUID   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS community_comment_likes (
    id          BIGSERIAL PRIMARY KEY,
    comment_id  BIGINT NOT NULL REFERENCES community_comments(id) ON DELETE CASCADE,
    user_id     UUID   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (comment_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_post_likes_post_id    ON community_post_likes(post_id);
CREATE INDEX IF NOT EXISTS idx_post_likes_user_id    ON community_post_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_comment_likes_comment_id ON community_comment_likes(comment_id);
CREATE INDEX IF NOT EXISTS idx_comment_likes_user_id    ON community_comment_likes(user_id);
"""


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(SQL)
    await conn.close()
    print("완료 — community_post_likes, community_comment_likes 테이블 생성(또는 이미 존재)")


if __name__ == "__main__":
    asyncio.run(main())
