"""daily_quiz_assignments 테이블 생성 + health_quizzes.quiz_date nullable 변경 스크립트.

실행 방법:
    docker cp scripts/migrate_daily_quiz_assignments.py fastapi:/tmp/migrate_daily_quiz_assignments.py
    docker exec -i fastapi uv run --no-sync python /tmp/migrate_daily_quiz_assignments.py

이미 존재하는 테이블 및 이미 nullable인 컬럼은 건너뜁니다 (멱등 실행 가능).
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
-- health_quizzes.quiz_date를 nullable로 변경
ALTER TABLE health_quizzes
    ALTER COLUMN quiz_date DROP NOT NULL;

-- daily_quiz_assignments 테이블 생성
CREATE TABLE IF NOT EXISTS daily_quiz_assignments (
    id             BIGSERIAL PRIMARY KEY,
    user_id        UUID   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quiz_id        BIGINT NOT NULL REFERENCES health_quizzes(id) ON DELETE CASCADE,
    assigned_date  DATE   NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, quiz_id, assigned_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_quiz_assignments_user_date
    ON daily_quiz_assignments(user_id, assigned_date);
"""


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(SQL)
    await conn.close()
    print("완료 — quiz_date nullable 변경, daily_quiz_assignments 테이블 생성(또는 이미 존재)")


if __name__ == "__main__":
    asyncio.run(main())
