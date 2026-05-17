from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(40) NOT NULL,
    "hashed_password" VARCHAR(128) NOT NULL,
    "name" VARCHAR(20) NOT NULL,
    "gender" VARCHAR(6) NOT NULL,
    "birthday" DATE NOT NULL,
    "phone_number" VARCHAR(11) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "last_login" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."gender" IS 'MALE: MALE\nFEMALE: FEMALE';
CREATE TABLE IF NOT EXISTS "disease_risk_guidelines" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "disease_type" VARCHAR(14) NOT NULL,
    "risk_level" VARCHAR(9) NOT NULL,
    "level_label" VARCHAR(40) NOT NULL,
    "condition_desc" TEXT NOT NULL,
    "recommendation" TEXT NOT NULL,
    "lifestyle_tips" JSONB NOT NULL,
    "hospital_visit_recommended" BOOL NOT NULL DEFAULT False,
    "disclaimer" TEXT NOT NULL,
    CONSTRAINT "uid_disease_ris_disease_428d63" UNIQUE ("disease_type", "risk_level")
);
COMMENT ON COLUMN "disease_risk_guidelines"."disease_type" IS 'DIABETES: DIABETES\nHYPERTENSION: HYPERTENSION\nCARDIOVASCULAR: CARDIOVASCULAR';
COMMENT ON COLUMN "disease_risk_guidelines"."risk_level" IS 'NORMAL: NORMAL\nCAUTION: CAUTION\nRISK: RISK\nHIGH_RISK: HIGH_RISK';
CREATE TABLE IF NOT EXISTS "disease_risks" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "disease_type" VARCHAR(14) NOT NULL,
    "risk_score" DECIMAL(5,2) NOT NULL,
    "risk_level" VARCHAR(9) NOT NULL,
    "contributing_factors" JSONB NOT NULL,
    "input_snapshot" JSONB NOT NULL,
    "model_version" VARCHAR(40) NOT NULL DEFAULT 'rule-v1',
    "calculated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "guideline_id" BIGINT REFERENCES "disease_risk_guidelines" ("id") ON DELETE SET NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_disease_ris_user_id_c1d19e" ON "disease_risks" ("user_id", "disease_type", "calculated_at");
COMMENT ON COLUMN "disease_risks"."disease_type" IS 'DIABETES: DIABETES\nHYPERTENSION: HYPERTENSION\nCARDIOVASCULAR: CARDIOVASCULAR';
COMMENT ON COLUMN "disease_risks"."risk_level" IS 'NORMAL: NORMAL\nCAUTION: CAUTION\nRISK: RISK\nHIGH_RISK: HIGH_RISK';
CREATE TABLE IF NOT EXISTS "health_records" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "record_type" VARCHAR(14) NOT NULL,
    "sub_type" VARCHAR(8),
    "primary_value" DECIMAL(8,2) NOT NULL,
    "secondary_value" DECIMAL(8,2),
    "unit" VARCHAR(16) NOT NULL,
    "measured_at" TIMESTAMPTZ NOT NULL,
    "source" VARCHAR(8) NOT NULL DEFAULT 'MANUAL',
    "note" TEXT,
    "is_deleted" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_health_reco_user_id_18f1a9" ON "health_records" ("user_id", "record_type", "measured_at");
COMMENT ON COLUMN "health_records"."record_type" IS 'WEIGHT: WEIGHT\nWAIST: WAIST\nBLOOD_PRESSURE: BLOOD_PRESSURE\nBLOOD_GLUCOSE: BLOOD_GLUCOSE\nHBA1C: HBA1C\nACTIVITY: ACTIVITY';
COMMENT ON COLUMN "health_records"."sub_type" IS 'HOME: HOME\nHOSPITAL: HOSPITAL\nFASTING: FASTING\nPOSTMEAL: POSTMEAL';
COMMENT ON COLUMN "health_records"."source" IS 'MANUAL: MANUAL\nWEARABLE: WEARABLE\nOCR: OCR';
CREATE TABLE IF NOT EXISTS "health_references" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "record_type" VARCHAR(14) NOT NULL,
    "sub_type" VARCHAR(8),
    "gender" VARCHAR(10),
    "age_group_min" SMALLINT,
    "age_group_max" SMALLINT,
    "normal_min" DECIMAL(8,2),
    "normal_max" DECIMAL(8,2),
    "caution_min" DECIMAL(8,2),
    "caution_max" DECIMAL(8,2),
    "danger_min" DECIMAL(8,2),
    "avg_value" DECIMAL(8,2),
    "source" VARCHAR(64),
    CONSTRAINT "uid_health_refe_record__f1982b" UNIQUE ("record_type", "sub_type", "gender", "age_group_min", "age_group_max")
);
COMMENT ON COLUMN "health_references"."record_type" IS 'WEIGHT: WEIGHT\nWAIST: WAIST\nBLOOD_PRESSURE: BLOOD_PRESSURE\nBLOOD_GLUCOSE: BLOOD_GLUCOSE\nHBA1C: HBA1C\nACTIVITY: ACTIVITY';
COMMENT ON COLUMN "health_references"."sub_type" IS 'HOME: HOME\nHOSPITAL: HOSPITAL\nFASTING: FASTING\nPOSTMEAL: POSTMEAL';
CREATE TABLE IF NOT EXISTS "monthly_reports" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "year_month" VARCHAR(7) NOT NULL,
    "disease_risk_summary" JSONB NOT NULL,
    "health_data_summary" JSONB NOT NULL,
    "challenge_summary" JSONB NOT NULL,
    "pdf_file_id" BIGINT,
    "generated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_monthly_rep_user_id_da02c2" UNIQUE ("user_id", "year_month")
);
CREATE TABLE IF NOT EXISTS "user_health_info" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "height_cm" DECIMAL(5,1),
    "weight_kg" DECIMAL(5,1),
    "waist_cm" DECIMAL(5,1),
    "is_smoker" BOOL NOT NULL DEFAULT False,
    "alcohol_intake" VARCHAR(8) NOT NULL DEFAULT 'NONE',
    "pregnancy_history" VARCHAR(14) NOT NULL DEFAULT 'NOT_APPLICABLE',
    "has_diabetes_family_history" BOOL NOT NULL DEFAULT False,
    "has_hypertension_family_history" BOOL NOT NULL DEFAULT False,
    "is_chronic_patient" BOOL NOT NULL DEFAULT False,
    "diseases" JSONB NOT NULL,
    "medications" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL UNIQUE REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "user_health_info"."alcohol_intake" IS 'NONE: NONE\nLIGHT: LIGHT\nMODERATE: MODERATE\nHEAVY: HEAVY';
COMMENT ON COLUMN "user_health_info"."pregnancy_history" IS 'NONE: NONE\nPREGNANT: PREGNANT\nPOSTPARTUM: POSTPARTUM\nNOT_APPLICABLE: NOT_APPLICABLE';
CREATE TABLE IF NOT EXISTS "rag_documents" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "document_type" VARCHAR(9) NOT NULL DEFAULT 'OTHER',
    "source" VARCHAR(200) NOT NULL,
    "title" VARCHAR(200),
    "chunk_index" INT NOT NULL DEFAULT 0,
    "chunk_text" TEXT NOT NULL,
    "embedding" vector(768),
    "metadata" JSONB NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_rag_documen_documen_075841" ON "rag_documents" ("document_type", "source");
CREATE INDEX IF NOT EXISTS "idx_rag_documen_is_acti_6a6f0b" ON "rag_documents" ("is_active");
COMMENT ON COLUMN "rag_documents"."document_type" IS 'GUIDELINE: GUIDELINE\nFAQ: FAQ\nEDUCATION: EDUCATION\nNOTICE: NOTICE\nOTHER: OTHER';
COMMENT ON TABLE "rag_documents" IS 'RAG / 챗봇 검색용 문서 청크.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
