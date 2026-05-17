from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "attendance_checks" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "check_date" DATE NOT NULL,
    "streak_days" INT NOT NULL DEFAULT 1,
    "bonus_awarded" BOOL NOT NULL DEFAULT False,
    "daily_point_amount" INT NOT NULL DEFAULT 0,
    "bonus_point_amount" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_attendance__user_id_61771b" UNIQUE ("user_id", "check_date")
);
CREATE INDEX IF NOT EXISTS "idx_attendance__user_id_61771b" ON "attendance_checks" ("user_id", "check_date");
        CREATE TABLE IF NOT EXISTS "items" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "category" VARCHAR(10) NOT NULL,
    "name" VARCHAR(80) NOT NULL,
    "description" TEXT,
    "price" INT NOT NULL DEFAULT 0,
    "thumbnail_file_id" BIGINT,
    "item_metadata" JSONB NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_items_categor_108ad6" ON "items" ("category", "is_active");
COMMENT ON COLUMN "items"."category" IS 'BACKGROUND: BACKGROUND\nFURNITURE: FURNITURE\nPET: PET\nTICKET: TICKET';
        CREATE TABLE IF NOT EXISTS "inventories" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "quantity" INT NOT NULL DEFAULT 1,
    "is_equipped" BOOL NOT NULL DEFAULT False,
    "acquired_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "item_id" BIGINT NOT NULL REFERENCES "items" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_inventories_user_id_d70061" UNIQUE ("user_id", "item_id")
);
CREATE INDEX IF NOT EXISTS "idx_inventories_user_id_df355d" ON "inventories" ("user_id", "is_equipped");
        CREATE TABLE IF NOT EXISTS "pets" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(20) NOT NULL,
    "pet_type" VARCHAR(5) NOT NULL DEFAULT 'DOG',
    "selected_style" VARCHAR(40),
    "level" INT NOT NULL DEFAULT 1,
    "current_xp" INT NOT NULL DEFAULT 0,
    "total_xp" INT NOT NULL DEFAULT 0,
    "hunger" INT NOT NULL DEFAULT 80,
    "cleanliness" INT NOT NULL DEFAULT 80,
    "mood" INT NOT NULL DEFAULT 80,
    "last_interacted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL UNIQUE REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "pets"."pet_type" IS 'DOG: DOG\nCAT: CAT\nPLANT: PLANT';
        CREATE TABLE IF NOT EXISTS "point_transactions" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "type" VARCHAR(5) NOT NULL,
    "amount" INT NOT NULL,
    "balance_after" INT NOT NULL DEFAULT 0,
    "source" VARCHAR(21) NOT NULL,
    "source_id" BIGINT,
    "description" VARCHAR(200),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_point_trans_user_id_396496" ON "point_transactions" ("user_id", "created_at");
CREATE INDEX IF NOT EXISTS "idx_point_trans_user_id_6654aa" ON "point_transactions" ("user_id", "source");
COMMENT ON COLUMN "point_transactions"."type" IS 'EARN: EARN\nSPEND: SPEND';
COMMENT ON COLUMN "point_transactions"."source" IS 'CHALLENGE_DAILY: CHALLENGE_DAILY\nCHALLENGE_PERIOD: CHALLENGE_PERIOD\nCHALLENGE_GROUP: CHALLENGE_GROUP\nCHALLENGE_WEEKLY_RANK: CHALLENGE_WEEKLY_RANK\nATTENDANCE_DAILY: ATTENDANCE_DAILY\nATTENDANCE_BONUS: ATTENDANCE_BONUS\nQUIZ: QUIZ\nSTORE_PURCHASE: STORE_PURCHASE\nPET_INTERACTION: PET_INTERACTION\nREFUND: REFUND\nETC: ETC';
        CREATE TABLE IF NOT EXISTS "rescue_ticket_usages" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "used_date" DATE NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "challenge_id" BIGINT NOT NULL REFERENCES "challenges" ("id") ON DELETE CASCADE,
    "inventory_id" BIGINT NOT NULL REFERENCES "inventories" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_rescue_tick_user_id_180d6f" ON "rescue_ticket_usages" ("user_id", "used_date");
CREATE INDEX IF NOT EXISTS "idx_rescue_tick_challen_41d5d1" ON "rescue_ticket_usages" ("challenge_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "point_transactions";
        DROP TABLE IF EXISTS "items";
        DROP TABLE IF EXISTS "attendance_checks";
        DROP TABLE IF EXISTS "pets";
        DROP TABLE IF EXISTS "inventories";
        DROP TABLE IF EXISTS "rescue_ticket_usages";"""


MODELS_STATE = (
    "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"
    "8BQkl6oQ=="
)
