from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chatbot_faqs" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "admin_id" BIGINT,
    "category" VARCHAR(9) NOT NULL,
    "question" VARCHAR(200) NOT NULL,
    "answer" TEXT NOT NULL,
    "sort_order" INT NOT NULL DEFAULT 0,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_chatbot_faq_categor_f92653" ON "chatbot_faqs" ("category", "is_active", "sort_order");
COMMENT ON COLUMN "chatbot_faqs"."category" IS 'SERVICE: SERVICE\nDISEASE: DISEASE\nCHALLENGE: CHALLENGE\nACCOUNT: ACCOUNT';
        CREATE TABLE IF NOT EXISTS "chatbot_sessions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(120),
    "started_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ended_at" TIMESTAMPTZ,
    "last_message_at" TIMESTAMPTZ,
    "message_count" INT NOT NULL DEFAULT 0,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chatbot_ses_user_id_71d782" ON "chatbot_sessions" ("user_id", "started_at");
        CREATE TABLE IF NOT EXISTS "chatbot_messages" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "role" VARCHAR(4) NOT NULL,
    "message_type" VARCHAR(6) NOT NULL DEFAULT 'TEXT',
    "content" TEXT NOT NULL,
    "sources" JSONB NOT NULL,
    "confidence" DOUBLE PRECISION,
    "model_version" VARCHAR(40),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "faq_id" BIGINT REFERENCES "chatbot_faqs" ("id") ON DELETE SET NULL,
    "session_id" BIGINT NOT NULL REFERENCES "chatbot_sessions" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chatbot_mes_session_aa3c71" ON "chatbot_messages" ("session_id", "created_at");
COMMENT ON COLUMN "chatbot_messages"."role" IS 'USER: USER\nBOT: BOT';
COMMENT ON COLUMN "chatbot_messages"."message_type" IS 'TEXT: TEXT\nFAQ: FAQ\nRAG: RAG\nSYSTEM: SYSTEM';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "chatbot_sessions";
        DROP TABLE IF EXISTS "chatbot_messages";
        DROP TABLE IF EXISTS "chatbot_faqs";"""


MODELS_STATE = (
    "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"
)
