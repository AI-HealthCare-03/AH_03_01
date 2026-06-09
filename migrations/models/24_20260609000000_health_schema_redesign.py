from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """UserHealthInfo 를 예측 모델 28개 입력 변수 기준으로 재구성.

    변경 내용:
    - 기존 user_health_info 컬럼 전부 드랍 후 신규 스키마로 재생성(기존 데이터 폐기 동의됨)
    - HealthRecord.record_type: HBA1C 제거, SLEEP/WATER 추가
    - HealthRecord.sub_type: POSTMEAL 제거
    - health_references.record_type / sub_type CHECK 제약조건도 동일하게 갱신
    """
    return """
        DROP TABLE IF EXISTS "user_health_info";

        CREATE TABLE "user_health_info" (
            "id"                     BIGSERIAL PRIMARY KEY,
            "user_id"                UUID NOT NULL UNIQUE
                                         REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
            "height_cm"              NUMERIC(5, 1),
            "weight_kg"              NUMERIC(5, 1),
            "waist_cm"               NUMERIC(5, 1),
            "systolic_bp"            NUMERIC(5, 1),
            "diastolic_bp"           NUMERIC(5, 1),
            "fasting_blood_sugar"    NUMERIC(6, 1),
            "sleep_weekday"          NUMERIC(4, 2),
            "sleep_weekend"          NUMERIC(4, 2),
            "moderate_exercise_hour" NUMERIC(4, 2),
            "mid_act_day"            SMALLINT,
            "walk_day"               SMALLINT,
            "water_count"            SMALLINT,
            "family_dm"              SMALLINT,
            "family_hp"              SMALLINT,
            "family_hl"              SMALLINT,
            "current_smoker"         SMALLINT,
            "smoking_risk"           NUMERIC(3, 1),
            "alcohol_freq_y"         SMALLINT,
            "alcohol_cup"            SMALLINT,
            "fruit_freq"             SMALLINT,
            "veg_freq_1"             SMALLINT,
            "out_meal_freq"          SMALLINT,
            "breakfast_freq"         SMALLINT,
            "is_menopause"           SMALLINT,
            "ocp_total_months"       SMALLINT,
            "anemia"                 SMALLINT,
            "chronic_diseases"       JSONB NOT NULL DEFAULT '[]',
            "medications"            JSONB NOT NULL DEFAULT '[]',
            "pregnancy_status"       VARCHAR(20),
            "bp_measure_env"         VARCHAR(10),
            "created_at"             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at"             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE "health_records"
            DROP CONSTRAINT IF EXISTS "health_records_record_type_check";

        ALTER TABLE "health_records"
            ADD CONSTRAINT "health_records_record_type_check"
            CHECK ("record_type" IN (
                'WEIGHT', 'WAIST', 'BLOOD_PRESSURE', 'BLOOD_GLUCOSE',
                'ACTIVITY', 'SLEEP', 'WATER'
            ));

        ALTER TABLE "health_records"
            DROP CONSTRAINT IF EXISTS "health_records_sub_type_check";

        ALTER TABLE "health_records"
            ADD CONSTRAINT "health_records_sub_type_check"
            CHECK ("sub_type" IS NULL OR "sub_type" IN ('HOME', 'HOSPITAL', 'FASTING'));

        ALTER TABLE "health_references"
            DROP CONSTRAINT IF EXISTS "health_references_record_type_check";

        ALTER TABLE "health_references"
            ADD CONSTRAINT "health_references_record_type_check"
            CHECK ("record_type" IN (
                'WEIGHT', 'WAIST', 'BLOOD_PRESSURE', 'BLOOD_GLUCOSE',
                'ACTIVITY', 'SLEEP', 'WATER'
            ));

        ALTER TABLE "health_references"
            DROP CONSTRAINT IF EXISTS "health_references_sub_type_check";

        ALTER TABLE "health_references"
            ADD CONSTRAINT "health_references_sub_type_check"
            CHECK ("sub_type" IS NULL OR "sub_type" IN ('HOME', 'HOSPITAL', 'FASTING'));
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "user_health_info";

        CREATE TABLE "user_health_info" (
            "id"                              BIGSERIAL PRIMARY KEY,
            "user_id"                         UUID NOT NULL UNIQUE
                                                  REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
            "height_cm"                       NUMERIC(5, 1),
            "weight_kg"                       NUMERIC(5, 1),
            "waist_cm"                        NUMERIC(5, 1),
            "is_smoker"                       BOOLEAN NOT NULL DEFAULT FALSE,
            "alcohol_intake"                  VARCHAR(10) NOT NULL DEFAULT 'NONE',
            "pregnancy_history"               VARCHAR(20) NOT NULL DEFAULT 'NOT_APPLICABLE',
            "has_diabetes_family_history"     BOOLEAN NOT NULL DEFAULT FALSE,
            "has_hypertension_family_history" BOOLEAN NOT NULL DEFAULT FALSE,
            "is_chronic_patient"              BOOLEAN NOT NULL DEFAULT FALSE,
            "diseases"                        JSONB NOT NULL DEFAULT '[]',
            "medications"                     JSONB NOT NULL DEFAULT '[]',
            "created_at"                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at"                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE "health_records"
            DROP CONSTRAINT IF EXISTS "health_records_record_type_check";

        ALTER TABLE "health_records"
            ADD CONSTRAINT "health_records_record_type_check"
            CHECK ("record_type" IN (
                'WEIGHT', 'WAIST', 'BLOOD_PRESSURE', 'BLOOD_GLUCOSE', 'HBA1C', 'ACTIVITY'
            ));

        ALTER TABLE "health_records"
            DROP CONSTRAINT IF EXISTS "health_records_sub_type_check";

        ALTER TABLE "health_records"
            ADD CONSTRAINT "health_records_sub_type_check"
            CHECK ("sub_type" IS NULL OR "sub_type" IN (
                'HOME', 'HOSPITAL', 'FASTING', 'POSTMEAL'
            ));

        ALTER TABLE "health_references"
            DROP CONSTRAINT IF EXISTS "health_references_record_type_check";

        ALTER TABLE "health_references"
            ADD CONSTRAINT "health_references_record_type_check"
            CHECK ("record_type" IN (
                'WEIGHT', 'WAIST', 'BLOOD_PRESSURE', 'BLOOD_GLUCOSE', 'HBA1C', 'ACTIVITY'
            ));

        ALTER TABLE "health_references"
            DROP CONSTRAINT IF EXISTS "health_references_sub_type_check";

        ALTER TABLE "health_references"
            ADD CONSTRAINT "health_references_sub_type_check"
            CHECK ("sub_type" IS NULL OR "sub_type" IN (
                'HOME', 'HOSPITAL', 'FASTING', 'POSTMEAL'
            ));
    """
