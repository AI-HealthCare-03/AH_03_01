from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE UNIQUE INDEX "uid_point_tran_user_id_source_source_id"
            ON "point_transactions" ("user_id", "source", "source_id")
            WHERE "source_id" IS NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_point_tran_user_id_source_source_id";"""
