"""
Migration: quiz-recycling
- quiz_attempts 의 구버전 (user_id, quiz_id) UNIQUE 제약을 제거하고
- 일일 멱등성을 보장하는 (user_id, quiz_id, attempted_date) UNIQUE + attempted_date 컬럼을 추가.
- 멱등 실행 가능 (이미 적용된 단계는 스킵).

실행:
    docker cp scripts/migrate_quiz_recycling.py fastapi:/tmp/migrate_quiz_recycling.py
    docker exec -i fastapi uv run --no-sync python /tmp/migrate_quiz_recycling.py
"""

import asyncio
import os
import sys

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core import config  # noqa: E402

# 삭제 대상 구 제약 이름 (Tortoise 자동생성 패턴)
OLD_CONSTRAINT = "quiz_attempts_user_id_quiz_id_key"
# 신규 제약 이름
NEW_CONSTRAINT = "quiz_attempts_user_quiz_date_key"


async def run() -> None:
    conn = await asyncpg.connect(
        host=config.DB_HOST,
        port=int(config.DB_PORT),
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )

    try:
        # 1. 구 (user_id, quiz_id) UNIQUE 제약 제거 — 이름 지정으로 다른 제약 보호
        old_exists = await conn.fetchval(
            """
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = 'quiz_attempts'
              AND constraint_name = $1
              AND constraint_type = 'UNIQUE'
            """,
            OLD_CONSTRAINT,
        )
        if old_exists:
            await conn.execute(f'ALTER TABLE quiz_attempts DROP CONSTRAINT "{OLD_CONSTRAINT}"')
            print(f"[migrate] 구 제약 삭제 완료: {OLD_CONSTRAINT}")
        else:
            print(f"[migrate] 구 제약 없음(이미 삭제됨): {OLD_CONSTRAINT}")

        # 2. attempted_date 컬럼 추가 (없을 때만)
        col_exists = await conn.fetchval(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'quiz_attempts' AND column_name = 'attempted_date'
            """
        )
        if not col_exists:
            await conn.execute("ALTER TABLE quiz_attempts ADD COLUMN attempted_date DATE")
            # 기존 데이터 backfill: attempted_at → Seoul(+09:00) 기준 날짜
            await conn.execute(
                "UPDATE quiz_attempts"
                " SET attempted_date = (attempted_at AT TIME ZONE 'Asia/Seoul')::date"
                " WHERE attempted_date IS NULL"
            )
            await conn.execute("ALTER TABLE quiz_attempts ALTER COLUMN attempted_date SET NOT NULL")
            print("[migrate] attempted_date 컬럼 추가 및 backfill 완료")
        else:
            print("[migrate] attempted_date 컬럼 이미 존재 — 스킵")

        # 3. 신규 (user_id, quiz_id, attempted_date) UNIQUE 추가 (없을 때만)
        new_exists = await conn.fetchval(
            """
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = 'quiz_attempts'
              AND constraint_name = $1
              AND constraint_type = 'UNIQUE'
            """,
            NEW_CONSTRAINT,
        )
        if not new_exists:
            await conn.execute(
                f'ALTER TABLE quiz_attempts ADD CONSTRAINT "{NEW_CONSTRAINT}"'
                " UNIQUE (user_id, quiz_id, attempted_date)"
            )
            print(f"[migrate] 신규 일일 UNIQUE 제약 추가 완료: {NEW_CONSTRAINT}")
        else:
            print(f"[migrate] 신규 제약 이미 존재 — 스킵: {NEW_CONSTRAINT}")

        print("[migrate] 완료")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
