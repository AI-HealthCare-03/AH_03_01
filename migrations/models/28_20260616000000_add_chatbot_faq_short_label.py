from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """chatbot_faqs 에 short_label(VARCHAR(20)) 컬럼 추가.

    FAQ 칩 UI에서 question 전체 대신 표시할 짧은 라벨(예: "비밀번호 재설정").
    """
    return """
        ALTER TABLE "chatbot_faqs"
            ADD COLUMN IF NOT EXISTS "short_label" VARCHAR(20);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chatbot_faqs"
            DROP COLUMN IF EXISTS "short_label";
    """
