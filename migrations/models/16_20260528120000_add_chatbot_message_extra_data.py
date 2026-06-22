from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """ChatbotMessage.extra_data JSONField(null=True) 추가.

    ChatRAGGraph 결과의 부가 메타 (intent / needs_health_data / missing_fields /
    action_hint / is_fallback / eval_revision_count / disclaimer) 를 메시지 단위로
    영속화. 이력 조회(`GET /chat/sessions/{id}`) 와 디버깅·RAGAS 평가용.

    기존 행은 NULL 로 채워지므로 데이터 손실 없음.
    """
    return """
        ALTER TABLE "chatbot_messages"
        ADD COLUMN "extra_data" JSONB;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chatbot_messages"
        DROP COLUMN "extra_data";
    """
