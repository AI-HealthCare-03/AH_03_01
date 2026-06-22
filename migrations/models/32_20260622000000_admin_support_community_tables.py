from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """관리자/문의/신고 도메인 스키마를 aerich 추적 마이그레이션으로 편입.

    기존에는 migrations/admin_system.sql(번호 없는 비추적 SQL)로만 존재해, 신규(fresh) 프로덕션에서
    `aerich upgrade` 시 생성되지 않아 첫 쿼리에서 크래시가 났다. 본 마이그레이션이 이를 대체한다.

    - community_posts: info_category / is_deleted 컬럼 추가 (모델 app.models.community.Post 정합)
    - support_faqs / support_inquiries / support_inquiry_answers (app.models.support)
    - community_reports (app.models.community.Report)

    개발 DB 에는 admin_system.sql 이 이미 수동 적용돼 있으므로 IF NOT EXISTS 로 idempotent 하게 둔다.
    """
    return """
        ALTER TABLE "community_posts" ADD COLUMN IF NOT EXISTS "info_category" VARCHAR(20);
        ALTER TABLE "community_posts" ADD COLUMN IF NOT EXISTS "is_deleted" BOOL NOT NULL DEFAULT FALSE;

        CREATE TABLE IF NOT EXISTS "support_faqs" (
            "id"         BIGSERIAL PRIMARY KEY,
            "question"   TEXT NOT NULL,
            "answer"     TEXT NOT NULL,
            "category"   VARCHAR(20) NOT NULL,
            "order"      INT NOT NULL DEFAULT 0,
            "is_active"  BOOL NOT NULL DEFAULT TRUE,
            "is_deleted" BOOL NOT NULL DEFAULT FALSE,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS "support_inquiries" (
            "id"             BIGSERIAL PRIMARY KEY,
            "user_id"        UUID NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
            "title"          VARCHAR(200) NOT NULL,
            "content"        TEXT NOT NULL,
            "category"       VARCHAR(30) NOT NULL,
            "attachment_url" VARCHAR(512),
            "status"         VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            "created_at"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at"     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS "support_inquiry_answers" (
            "id"         BIGSERIAL PRIMARY KEY,
            "inquiry_id" BIGINT NOT NULL UNIQUE REFERENCES "support_inquiries"("id") ON DELETE CASCADE,
            "content"    TEXT NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS "community_reports" (
            "id"          BIGSERIAL PRIMARY KEY,
            "target_type" VARCHAR(30) NOT NULL,
            "target_id"   BIGINT NOT NULL,
            "reason"      VARCHAR(20) NOT NULL,
            "reporter_id" UUID NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
            "created_at"  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT "uq_report_reporter_target" UNIQUE ("reporter_id", "target_type", "target_id")
        );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "community_reports";
        DROP TABLE IF EXISTS "support_inquiry_answers";
        DROP TABLE IF EXISTS "support_inquiries";
        DROP TABLE IF EXISTS "support_faqs";
        ALTER TABLE "community_posts" DROP COLUMN IF EXISTS "is_deleted";
        ALTER TABLE "community_posts" DROP COLUMN IF EXISTS "info_category";
    """
