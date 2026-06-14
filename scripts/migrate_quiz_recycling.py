"""
Migration: quiz-recycling
- quiz_attempts 테이블의 (user_id, quiz_id) unique 제약 조건 제거
- 3일 쿨다운 후 퀴즈 재출제를 위해 중복 attempt를 허용
"""

import asyncio
import os
import sys

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core import config  # noqa: E402


async def run() -> None:
    conn = await asyncpg.connect(
        host=config.DB_HOST,
        port=int(config.DB_PORT),
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )

    try:
        # quiz_attempts 테이블의 unique 제약 조건 이름 조회
        rows = await conn.fetch(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'quiz_attempts'
              AND constraint_type = 'UNIQUE'
            """
        )

        if not rows:
            print("[migrate_quiz_recycling] quiz_attempts 에 UNIQUE 제약이 없습니다 — 이미 적용됨")
            return

        for row in rows:
            constraint_name = row["constraint_name"]
            await conn.execute(f'ALTER TABLE quiz_attempts DROP CONSTRAINT IF EXISTS "{constraint_name}"')
            print(f"[migrate_quiz_recycling] 제약 조건 삭제 완료: {constraint_name}")

        print("[migrate_quiz_recycling] 완료: quiz_attempts UNIQUE 제약 제거됨")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
