"""info_category 컬럼 마이그레이션 스크립트.

실행 방법:
    docker cp scripts/migrate_info_category.py fastapi:/tmp/migrate_info_category.py
    docker exec -i fastapi uv run --no-sync python /tmp/migrate_info_category.py
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
ALTER TABLE community_posts
    ADD COLUMN IF NOT EXISTS info_category VARCHAR(20) NULL;
"""


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(SQL)
    await conn.close()
    print("완료 — info_category 컬럼 추가됨")


if __name__ == "__main__":
    asyncio.run(main())
