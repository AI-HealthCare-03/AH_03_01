from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """펫 상태 악화(6번) 및 약 회복(7번) 백로그를 위한 컬럼 추가.

    - pets.intimacy : 친밀도 (0~100, 약 회복 등에 사용)
    - pets.sick      : 아픔 상태 (hunger 가 0 이 되면 true)
    - pets.last_decay_at : lazy decay 계산 기준 시각

    MEDICINE enum 값 추가는 코드 측에서만 반영
    (items.category 는 VARCHAR 컬럼이므로 DB 스키마 변경 없음)
    """
    return """
        ALTER TABLE "pets" ADD COLUMN "intimacy" INT NOT NULL DEFAULT 0;
        ALTER TABLE "pets" ADD COLUMN "sick" BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE "pets" ADD COLUMN "last_decay_at" TIMESTAMPTZ;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "pets" DROP COLUMN "last_decay_at";
        ALTER TABLE "pets" DROP COLUMN "sick";
        ALTER TABLE "pets" DROP COLUMN "intimacy";
    """
