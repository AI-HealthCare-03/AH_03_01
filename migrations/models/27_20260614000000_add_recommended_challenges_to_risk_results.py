from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """risk_recommendation_results 에 recommended_challenges(JSONB) 컬럼 추가.

    프론트 카드용 구조화 추천 챌린지(template_id/title/category/difficulty/reason/priority)를
    이력에도 함께 영속화한다. 서빙(Redis) 캐시는 응답 JSON 전체를 보관하므로 별도 변경 불필요.
    """
    return """
        ALTER TABLE "risk_recommendation_results"
            ADD COLUMN IF NOT EXISTS "recommended_challenges" JSONB NOT NULL DEFAULT '[]';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "risk_recommendation_results"
            DROP COLUMN IF EXISTS "recommended_challenges";
    """
