from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "challenge_templates" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "category" VARCHAR(12) NOT NULL,
    "sub_category" VARCHAR(8),
    "title" VARCHAR(80) NOT NULL,
    "description" TEXT,
    "goal_type" VARCHAR(8) NOT NULL,
    "goal_value_options" JSONB NOT NULL,
    "default_unit" VARCHAR(20),
    "verification_type" VARCHAR(5) NOT NULL,
    "difficulty" VARCHAR(7) NOT NULL DEFAULT 'LEVEL_1',
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_challenge_t_categor_5556f5" ON "challenge_templates" ("category", "is_active");
COMMENT ON COLUMN "challenge_templates"."category" IS 'EXERCISE: EXERCISE\nWATER: WATER\nSLEEP: SLEEP\nDIET: DIET\nNO_SMOKING: NO_SMOKING\nNO_ALCOHOL: NO_ALCOHOL\nDISEASE_CARE: DISEASE_CARE\nMEDITATION: MEDITATION';
COMMENT ON COLUMN "challenge_templates"."sub_category" IS 'WALKING: WALKING\nRUNNING: RUNNING\nSTRENGTH: STRENGTH\nCYCLING: CYCLING\nSWIMMING: SWIMMING\nOTHER: OTHER';
COMMENT ON COLUMN "challenge_templates"."goal_type" IS 'DURATION: DURATION\nCOUNT: COUNT\nAMOUNT: AMOUNT\nCHECK: CHECK';
COMMENT ON COLUMN "challenge_templates"."verification_type" IS 'CHECK: CHECK\nPHOTO: PHOTO';
COMMENT ON COLUMN "challenge_templates"."difficulty" IS 'LEVEL_1: LEVEL_1\nLEVEL_2: LEVEL_2\nLEVEL_3: LEVEL_3\nLEVEL_4: LEVEL_4';
        CREATE TABLE IF NOT EXISTS "challenges" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(120) NOT NULL,
    "description" TEXT,
    "category" VARCHAR(12) NOT NULL,
    "sub_category" VARCHAR(8),
    "scope" VARCHAR(8) NOT NULL DEFAULT 'PERSONAL',
    "goal_type" VARCHAR(8) NOT NULL,
    "goal_value" DECIMAL(10,2),
    "unit" VARCHAR(20),
    "verification_type" VARCHAR(5) NOT NULL,
    "difficulty" VARCHAR(7) NOT NULL DEFAULT 'LEVEL_1',
    "visibility" VARCHAR(7) NOT NULL DEFAULT 'PUBLIC',
    "status" VARCHAR(10) NOT NULL DEFAULT 'RECRUITING',
    "max_participants" INT NOT NULL DEFAULT 1,
    "start_date" DATE NOT NULL,
    "end_date" DATE NOT NULL,
    "is_deleted" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "creator_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "template_id" BIGINT REFERENCES "challenge_templates" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_challenges_status_781da6" ON "challenges" ("status", "scope");
CREATE INDEX IF NOT EXISTS "idx_challenges_creator_e60f9d" ON "challenges" ("creator_id", "status");
CREATE INDEX IF NOT EXISTS "idx_challenges_start_d_c12130" ON "challenges" ("start_date", "end_date");
COMMENT ON COLUMN "challenges"."category" IS 'EXERCISE: EXERCISE\nWATER: WATER\nSLEEP: SLEEP\nDIET: DIET\nNO_SMOKING: NO_SMOKING\nNO_ALCOHOL: NO_ALCOHOL\nDISEASE_CARE: DISEASE_CARE\nMEDITATION: MEDITATION';
COMMENT ON COLUMN "challenges"."sub_category" IS 'WALKING: WALKING\nRUNNING: RUNNING\nSTRENGTH: STRENGTH\nCYCLING: CYCLING\nSWIMMING: SWIMMING\nOTHER: OTHER';
COMMENT ON COLUMN "challenges"."scope" IS 'PERSONAL: PERSONAL\nGROUP: GROUP';
COMMENT ON COLUMN "challenges"."goal_type" IS 'DURATION: DURATION\nCOUNT: COUNT\nAMOUNT: AMOUNT\nCHECK: CHECK';
COMMENT ON COLUMN "challenges"."verification_type" IS 'CHECK: CHECK\nPHOTO: PHOTO';
COMMENT ON COLUMN "challenges"."difficulty" IS 'LEVEL_1: LEVEL_1\nLEVEL_2: LEVEL_2\nLEVEL_3: LEVEL_3\nLEVEL_4: LEVEL_4';
COMMENT ON COLUMN "challenges"."visibility" IS 'PUBLIC: PUBLIC\nPRIVATE: PRIVATE';
COMMENT ON COLUMN "challenges"."status" IS 'RECRUITING: RECRUITING\nACTIVE: ACTIVE\nCOMPLETED: COMPLETED\nCANCELLED: CANCELLED';
        CREATE TABLE IF NOT EXISTS "challenge_invites" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "invite_code" VARCHAR(12),
    "invite_type" VARCHAR(6) NOT NULL DEFAULT 'CODE',
    "status" VARCHAR(8) NOT NULL DEFAULT 'PENDING',
    "expires_at" TIMESTAMPTZ,
    "responded_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "challenge_id" BIGINT NOT NULL REFERENCES "challenges" ("id") ON DELETE CASCADE,
    "invitee_id" BIGINT REFERENCES "users" ("id") ON DELETE SET NULL,
    "inviter_id" BIGINT REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_challenge_i_invite__4d749d" ON "challenge_invites" ("invite_code");
CREATE INDEX IF NOT EXISTS "idx_challenge_i_invitee_286682" ON "challenge_invites" ("invitee_id", "status");
COMMENT ON COLUMN "challenge_invites"."invite_type" IS 'CODE: CODE\nDIRECT: DIRECT';
COMMENT ON COLUMN "challenge_invites"."status" IS 'PENDING: PENDING\nACCEPTED: ACCEPTED\nREJECTED: REJECTED\nEXPIRED: EXPIRED';
        CREATE TABLE IF NOT EXISTS "challenge_participants" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "role" VARCHAR(6) NOT NULL DEFAULT 'MEMBER',
    "status" VARCHAR(8) NOT NULL DEFAULT 'APPROVED',
    "current_score" INT NOT NULL DEFAULT 0,
    "missed_count" INT NOT NULL DEFAULT 0,
    "joined_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "left_at" TIMESTAMPTZ,
    "challenge_id" BIGINT NOT NULL REFERENCES "challenges" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_challenge_p_challen_7aab77" UNIQUE ("challenge_id", "user_id")
);
CREATE INDEX IF NOT EXISTS "idx_challenge_p_challen_286e3f" ON "challenge_participants" ("challenge_id", "status");
CREATE INDEX IF NOT EXISTS "idx_challenge_p_user_id_6d6be1" ON "challenge_participants" ("user_id", "status");
COMMENT ON COLUMN "challenge_participants"."role" IS 'OWNER: OWNER\nMEMBER: MEMBER';
COMMENT ON COLUMN "challenge_participants"."status" IS 'PENDING: PENDING\nAPPROVED: APPROVED\nREJECTED: REJECTED\nLEFT: LEFT\nKICKED: KICKED';
        CREATE TABLE IF NOT EXISTS "challenge_verifications" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "method" VARCHAR(6) NOT NULL,
    "verified_date" DATE NOT NULL,
    "checked" BOOL,
    "answers" JSONB,
    "photo_file_id" BIGINT,
    "shield_inventory_id" BIGINT,
    "status" VARCHAR(8) NOT NULL DEFAULT 'PENDING',
    "rejection_reason" TEXT,
    "like_count" INT NOT NULL DEFAULT 0,
    "comment_count" INT NOT NULL DEFAULT 0,
    "is_deleted" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "challenge_id" BIGINT NOT NULL REFERENCES "challenges" ("id") ON DELETE CASCADE,
    "participant_id" BIGINT NOT NULL REFERENCES "challenge_participants" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_challenge_v_partici_81eb7b" UNIQUE ("participant_id", "verified_date", "method")
);
CREATE INDEX IF NOT EXISTS "idx_challenge_v_challen_898fef" ON "challenge_verifications" ("challenge_id", "verified_date");
CREATE INDEX IF NOT EXISTS "idx_challenge_v_user_id_54fac6" ON "challenge_verifications" ("user_id", "verified_date");
COMMENT ON COLUMN "challenge_verifications"."method" IS 'CHECK: CHECK\nPHOTO: PHOTO\nSHIELD: SHIELD';
COMMENT ON COLUMN "challenge_verifications"."status" IS 'PENDING: PENDING\nAPPROVED: APPROVED\nREJECTED: REJECTED';
        CREATE TABLE IF NOT EXISTS "challenge_reactions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "type" VARCHAR(7) NOT NULL,
    "content" TEXT,
    "is_deleted" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "verification_id" BIGINT NOT NULL REFERENCES "challenge_verifications" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_challenge_r_verific_21d997" ON "challenge_reactions" ("verification_id", "type");
CREATE INDEX IF NOT EXISTS "idx_challenge_r_user_id_5dd75c" ON "challenge_reactions" ("user_id", "type");
COMMENT ON COLUMN "challenge_reactions"."type" IS 'LIKE: LIKE\nCOMMENT: COMMENT';
        CREATE TABLE IF NOT EXISTS "challenge_recommendations" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "priority" VARCHAR(11) NOT NULL DEFAULT 'RECOMMENDED',
    "reason" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "challenge_id" BIGINT REFERENCES "challenges" ("id") ON DELETE SET NULL,
    "disease_risk_id" BIGINT REFERENCES "disease_risks" ("id") ON DELETE SET NULL,
    "template_id" BIGINT REFERENCES "challenge_templates" ("id") ON DELETE SET NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_challenge_r_user_id_27a616" ON "challenge_recommendations" ("user_id", "priority", "created_at");
COMMENT ON COLUMN "challenge_recommendations"."priority" IS 'TOP: TOP\nRECOMMENDED: RECOMMENDED\nOPTIONAL: OPTIONAL';
        CREATE TABLE IF NOT EXISTS "challenge_verification_attachments" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "file_id" BIGINT NOT NULL,
    "sort_order" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "verification_id" BIGINT NOT NULL REFERENCES "challenge_verifications" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_challenge_v_verific_3e64af" ON "challenge_verification_attachments" ("verification_id", "sort_order");
        CREATE TABLE IF NOT EXISTS "image_verification_jobs" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(7) NOT NULL DEFAULT 'QUEUED',
    "result" JSONB NOT NULL,
    "model_version" VARCHAR(40) NOT NULL DEFAULT 'siglip2-stub-v0',
    "error_message" TEXT,
    "queued_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "started_at" TIMESTAMPTZ,
    "completed_at" TIMESTAMPTZ,
    "verification_id" BIGINT NOT NULL REFERENCES "challenge_verifications" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_image_verif_status_e5d7bb" ON "image_verification_jobs" ("status", "queued_at");
COMMENT ON COLUMN "image_verification_jobs"."status" IS 'QUEUED: QUEUED\nRUNNING: RUNNING\nSUCCESS: SUCCESS\nFAILED: FAILED';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "challenge_participants";
        DROP TABLE IF EXISTS "challenge_verifications";
        DROP TABLE IF EXISTS "challenge_reactions";
        DROP TABLE IF EXISTS "challenge_verification_attachments";
        DROP TABLE IF EXISTS "image_verification_jobs";
        DROP TABLE IF EXISTS "challenge_recommendations";
        DROP TABLE IF EXISTS "challenge_invites";
        DROP TABLE IF EXISTS "challenge_templates";
        DROP TABLE IF EXISTS "challenges";"""


MODELS_STATE = (
    "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"
    "r8ycK5PTGpzW4LRGMlrjx/8Dx4uYBg=="
)
