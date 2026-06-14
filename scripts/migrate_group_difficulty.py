"""기존 그룹 챌린지의 difficulty 필드를 goal_config 기반으로 재계산해 업데이트한다.

배경:
    챌린지 생성 시 difficulty 를 프론트에서 전달하지 않아 모든 그룹 챌린지가
    기본값 LEVEL_1 로 저장되어 있었다. 이 스크립트는 goal_config 의
    group_target_count / group_target_members 값을 보고 올바른 LEVEL 로 수정한다.

실행 방법:
    docker exec -i fastapi uv run --no-sync python scripts/migrate_group_difficulty.py

멱등 실행 가능 (여러 번 실행해도 결과 동일).
"""

import asyncio
import json
import os

import asyncpg

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "postgres"),
    port=int(os.getenv("DB_PORT", "5432")),
    user=os.getenv("DB_USER", "ozcoding"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_health"),
)

# GROUP_SUM: group_target_count 기준
GROUP_SUM_TABLE = [
    (35, "LEVEL_4"),
    (30, "LEVEL_3"),
    (15, "LEVEL_2"),
    (6,  "LEVEL_1"),
]

# GROUP_MEMBERS: group_target_members 기준
GROUP_MEMBERS_TABLE = [
    (5, "LEVEL_4"),
    (4, "LEVEL_3"),
    (3, "LEVEL_2"),
    (2, "LEVEL_1"),
]


def calc_difficulty(goal_config: dict) -> str:
    cfg = goal_config or {}
    if "group_target_count" in cfg:
        target = int(cfg["group_target_count"] or 0)
        table = GROUP_SUM_TABLE
    else:
        target = int(cfg.get("group_target_members") or 0)
        table = GROUP_MEMBERS_TABLE
    for threshold, level in table:
        if target >= threshold:
            return level
    return "LEVEL_1"


async def migrate() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # asyncpg는 JSONB를 기본적으로 str로 반환 → dict로 받으려면 codec 등록 필수
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

        rows = await conn.fetch(
            """
            SELECT id, goal_type, goal_config
            FROM challenges
            WHERE scope = 'GROUP'
            """
        )
        print(f"대상 그룹 챌린지: {len(rows)}건")

        updated = 0
        async with conn.transaction():  # 부분 적용 방지: 전체 성공 or 전체 롤백
            for row in rows:
                goal_type = row["goal_type"]
                goal_config = row["goal_config"] or {}
                correct = calc_difficulty(goal_config)

                await conn.execute(
                    "UPDATE challenges SET difficulty = $1 WHERE id = $2",
                    correct,
                    row["id"],
                )
                updated += 1
                print(f"  challenge_id={row['id']} goal_type={goal_type} → {correct}")

        print(f"\n완료: {updated}건 업데이트")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
