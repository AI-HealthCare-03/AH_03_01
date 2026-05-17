from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """USER PK BigInt → UUID 전환.

    BigInt 를 직접 UUID 캐스트 불가하므로 백필+swap 전략:
    1) pgcrypto 활성화
    2) users.id_new (UUID) 생성 + 모든 기존 row 에 UUID 할당
    3) 모든 referencing 칼럼에 *_uuid 임시 칼럼 추가 + users.id_new 와 매핑하여 백필
    4) FK 제약 삭제
    5) 기존 BigInt 칼럼 DROP, *_uuid → 원래 명으로 RENAME
    6) users PK swap: id (bigint) 삭제 → id_new 를 id 로 RENAME, PK + DEFAULT gen_random_uuid()
    7) FK 제약 재생성
    """
    return """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;

        ALTER TABLE "users" ADD COLUMN "id_new" UUID NOT NULL DEFAULT gen_random_uuid();
        CREATE UNIQUE INDEX "users_id_new_uniq" ON "users"("id_new");

        ALTER TABLE "challenges" ADD COLUMN "creator_id_new" UUID NULL;
        UPDATE "challenges" t SET "creator_id_new" = u."id_new" FROM "users" u WHERE t."creator_id" = u."id";

        ALTER TABLE "challenge_participants" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "challenge_participants" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "challenge_invites" ADD COLUMN "inviter_id_new" UUID NULL;
        UPDATE "challenge_invites" t SET "inviter_id_new" = u."id_new" FROM "users" u WHERE t."inviter_id" = u."id";

        ALTER TABLE "challenge_invites" ADD COLUMN "invitee_id_new" UUID NULL;
        UPDATE "challenge_invites" t SET "invitee_id_new" = u."id_new" FROM "users" u WHERE t."invitee_id" = u."id";

        ALTER TABLE "challenge_verifications" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "challenge_verifications" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "challenge_reactions" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "challenge_reactions" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "challenge_recommendations" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "challenge_recommendations" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "file_uploads" ADD COLUMN "uploader_id_new" UUID NULL;
        UPDATE "file_uploads" t SET "uploader_id_new" = u."id_new" FROM "users" u WHERE t."uploader_id" = u."id";

        ALTER TABLE "pets" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "pets" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "inventories" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "inventories" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "point_transactions" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "point_transactions" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "attendance_checks" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "attendance_checks" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "rescue_ticket_usages" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "rescue_ticket_usages" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "xp_events" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "xp_events" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "chatbot_sessions" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "chatbot_sessions" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "user_health_info" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "user_health_info" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "health_records" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "health_records" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "disease_risks" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "disease_risks" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "monthly_reports" ADD COLUMN "user_id_new" UUID NULL;
        UPDATE "monthly_reports" t SET "user_id_new" = u."id_new" FROM "users" u WHERE t."user_id" = u."id";

        ALTER TABLE "users" ADD COLUMN "banned_by_new" UUID NULL;
        UPDATE "users" u SET "banned_by_new" = b."id_new" FROM "users" b WHERE u."banned_by" = b."id";

        DO $$ DECLARE r RECORD; BEGIN
            FOR r IN
                SELECT tc.constraint_name, tc.table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY' AND ccu.table_name='users'
            LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.constraint_name);
            END LOOP;
        END $$;

        ALTER TABLE "challenges" DROP COLUMN "creator_id";
        ALTER TABLE "challenges" RENAME COLUMN "creator_id_new" TO "creator_id";
        ALTER TABLE "challenge_participants" DROP COLUMN "user_id";
        ALTER TABLE "challenge_participants" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "challenge_invites" DROP COLUMN "inviter_id";
        ALTER TABLE "challenge_invites" RENAME COLUMN "inviter_id_new" TO "inviter_id";
        ALTER TABLE "challenge_invites" DROP COLUMN "invitee_id";
        ALTER TABLE "challenge_invites" RENAME COLUMN "invitee_id_new" TO "invitee_id";
        ALTER TABLE "challenge_verifications" DROP COLUMN "user_id";
        ALTER TABLE "challenge_verifications" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "challenge_reactions" DROP COLUMN "user_id";
        ALTER TABLE "challenge_reactions" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "challenge_recommendations" DROP COLUMN "user_id";
        ALTER TABLE "challenge_recommendations" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "file_uploads" DROP COLUMN "uploader_id";
        ALTER TABLE "file_uploads" RENAME COLUMN "uploader_id_new" TO "uploader_id";
        ALTER TABLE "pets" DROP COLUMN "user_id";
        ALTER TABLE "pets" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "inventories" DROP COLUMN "user_id";
        ALTER TABLE "inventories" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "point_transactions" DROP COLUMN "user_id";
        ALTER TABLE "point_transactions" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "attendance_checks" DROP COLUMN "user_id";
        ALTER TABLE "attendance_checks" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "rescue_ticket_usages" DROP COLUMN "user_id";
        ALTER TABLE "rescue_ticket_usages" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "xp_events" DROP COLUMN "user_id";
        ALTER TABLE "xp_events" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "chatbot_sessions" DROP COLUMN "user_id";
        ALTER TABLE "chatbot_sessions" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "user_health_info" DROP COLUMN "user_id";
        ALTER TABLE "user_health_info" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "health_records" DROP COLUMN "user_id";
        ALTER TABLE "health_records" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "disease_risks" DROP COLUMN "user_id";
        ALTER TABLE "disease_risks" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "monthly_reports" DROP COLUMN "user_id";
        ALTER TABLE "monthly_reports" RENAME COLUMN "user_id_new" TO "user_id";
        ALTER TABLE "users" DROP COLUMN "banned_by";
        ALTER TABLE "users" RENAME COLUMN "banned_by_new" TO "banned_by";

        ALTER TABLE "users" DROP CONSTRAINT IF EXISTS "users_pkey";
        ALTER TABLE "users" DROP COLUMN "id";
        ALTER TABLE "users" RENAME COLUMN "id_new" TO "id";
        ALTER TABLE "users" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
        ALTER TABLE "users" ADD PRIMARY KEY ("id");
        DROP INDEX IF EXISTS "users_id_new_uniq";

        ALTER TABLE "challenges" ADD CONSTRAINT "challenges_creator_id_fkey" FOREIGN KEY ("creator_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "challenge_participants" ADD CONSTRAINT "challenge_participants_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "challenge_invites" ADD CONSTRAINT "challenge_invites_inviter_id_fkey" FOREIGN KEY ("inviter_id") REFERENCES "users"("id") ON DELETE SET NULL;
        ALTER TABLE "challenge_invites" ADD CONSTRAINT "challenge_invites_invitee_id_fkey" FOREIGN KEY ("invitee_id") REFERENCES "users"("id") ON DELETE SET NULL;
        ALTER TABLE "challenge_verifications" ADD CONSTRAINT "challenge_verifications_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "challenge_reactions" ADD CONSTRAINT "challenge_reactions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "challenge_recommendations" ADD CONSTRAINT "challenge_recommendations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "file_uploads" ADD CONSTRAINT "file_uploads_uploader_id_fkey" FOREIGN KEY ("uploader_id") REFERENCES "users"("id") ON DELETE SET NULL;
        ALTER TABLE "pets" ADD CONSTRAINT "pets_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "inventories" ADD CONSTRAINT "inventories_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "point_transactions" ADD CONSTRAINT "point_transactions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "attendance_checks" ADD CONSTRAINT "attendance_checks_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "rescue_ticket_usages" ADD CONSTRAINT "rescue_ticket_usages_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "xp_events" ADD CONSTRAINT "xp_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "chatbot_sessions" ADD CONSTRAINT "chatbot_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "user_health_info" ADD CONSTRAINT "user_health_info_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "health_records" ADD CONSTRAINT "health_records_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "disease_risks" ADD CONSTRAINT "disease_risks_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
        ALTER TABLE "monthly_reports" ADD CONSTRAINT "monthly_reports_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "pets" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "users" ALTER COLUMN "banned_by" TYPE BIGINT USING "banned_by"::BIGINT;
        ALTER TABLE "xp_events" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "challenges" ALTER COLUMN "creator_id" TYPE BIGINT USING "creator_id"::BIGINT;
        ALTER TABLE "inventories" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "file_uploads" ALTER COLUMN "uploader_id" TYPE BIGINT USING "uploader_id"::BIGINT;
        ALTER TABLE "disease_risks" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "health_records" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "monthly_reports" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "chatbot_sessions" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_health_info" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "attendance_checks" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "challenge_invites" ALTER COLUMN "invitee_id" TYPE BIGINT USING "invitee_id"::BIGINT;
        ALTER TABLE "challenge_invites" ALTER COLUMN "inviter_id" TYPE BIGINT USING "inviter_id"::BIGINT;
        ALTER TABLE "point_transactions" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "challenge_reactions" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "rescue_ticket_usages" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "challenge_participants" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "challenge_verifications" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "challenge_recommendations" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;"""


MODELS_STATE = (
    "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"
    "f9Vu/Wk="
)
