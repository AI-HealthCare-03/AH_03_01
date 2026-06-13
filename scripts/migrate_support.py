"""고객지원 테이블 생성 스크립트 (support_faqs, support_inquiries, support_inquiry_answers).

실행 방법:
    docker cp scripts/migrate_support.py fastapi:/tmp/migrate_support.py
    docker exec -i fastapi uv run --no-sync python /tmp/migrate_support.py

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
CREATE TABLE IF NOT EXISTS support_faqs (
    id          BIGSERIAL PRIMARY KEY,
    question    TEXT        NOT NULL,
    answer      TEXT        NOT NULL,
    category    VARCHAR(20) NOT NULL,
    "order"     INTEGER     NOT NULL DEFAULT 0,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_faqs_category
    ON support_faqs(category);

CREATE TABLE IF NOT EXISTS support_inquiries (
    id             BIGSERIAL    PRIMARY KEY,
    user_id        UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(200) NOT NULL,
    content        TEXT         NOT NULL,
    category       VARCHAR(30)  NOT NULL,
    attachment_url VARCHAR(512),
    status         VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_inquiries_user_id
    ON support_inquiries(user_id);

CREATE TABLE IF NOT EXISTS support_inquiry_answers (
    id          BIGSERIAL PRIMARY KEY,
    inquiry_id  BIGINT    NOT NULL REFERENCES support_inquiries(id) ON DELETE CASCADE UNIQUE,
    content     TEXT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(SQL)
    await conn.close()
    print("완료 — support_faqs, support_inquiries, support_inquiry_answers 테이블 생성(또는 이미 존재)")


if __name__ == "__main__":
    asyncio.run(main())
