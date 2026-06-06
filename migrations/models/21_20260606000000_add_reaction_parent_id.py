from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "challenge_reactions" ADD COLUMN IF NOT EXISTS "parent_id" BIGINT REFERENCES "challenge_reactions" ("id") ON DELETE SET NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "challenge_reactions" DROP COLUMN IF EXISTS "parent_id";
    """
