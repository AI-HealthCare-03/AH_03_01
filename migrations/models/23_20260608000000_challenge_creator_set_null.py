from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """challenges.creator_id FK 를 ON DELETE CASCADE → SET NULL.

    회원 하드 삭제(30일 purge) 시 탈퇴 유저가 만든 챌린지가 cascade 로 통째 삭제되어
    다른 참여자들의 데이터까지 함께 사라지는 것을 DB 차원에서 차단한다. 컬럼도
    NOT NULL → NULL 허용으로 변경. (FK 인라인 자동명: challenges_creator_id_fkey)
    """
    return """
        ALTER TABLE "challenges" ALTER COLUMN "creator_id" DROP NOT NULL;
        ALTER TABLE "challenges" DROP CONSTRAINT IF EXISTS "challenges_creator_id_fkey";
        ALTER TABLE "challenges" ADD CONSTRAINT "challenges_creator_id_fkey"
            FOREIGN KEY ("creator_id") REFERENCES "users" ("id") ON DELETE SET NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "challenges" DROP CONSTRAINT IF EXISTS "challenges_creator_id_fkey";
        ALTER TABLE "challenges" ADD CONSTRAINT "challenges_creator_id_fkey"
            FOREIGN KEY ("creator_id") REFERENCES "users" ("id") ON DELETE CASCADE;
        ALTER TABLE "challenges" ALTER COLUMN "creator_id" SET NOT NULL;
    """
