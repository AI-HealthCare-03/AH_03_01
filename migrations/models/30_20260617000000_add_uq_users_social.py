from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """users (social_provider, social_id) 부분 유니크 인덱스 추가.

    카카오 등 소셜 계정의 중복 가입을 DB 레벨에서 차단한다.
    WHERE 절로 기존 NULL/NULL 행(일반 가입 계정)은 인덱스 대상에서 제외하므로
    기존 데이터를 건드리지 않고 안전하게 추가된다.
    """
    return """
        CREATE UNIQUE INDEX IF NOT EXISTS "uq_users_social_provider_social_id"
            ON "users" ("social_provider", "social_id")
            WHERE "social_provider" IS NOT NULL AND "social_id" IS NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uq_users_social_provider_social_id";
    """
