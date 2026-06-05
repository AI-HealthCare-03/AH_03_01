from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "challenge_verifications" ADD COLUMN IF NOT EXISTS "caption" TEXT;
        ALTER TABLE "challenge_verifications" ADD COLUMN IF NOT EXISTS "verified_duration_seconds" INT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "challenge_verifications" DROP COLUMN IF EXISTS "caption";
        ALTER TABLE "challenge_verifications" DROP COLUMN IF EXISTS "verified_duration_seconds";
    """
