-- ============================================================
-- 케어로그 prod RDS 마이그레이션 — 2026-06-17 (dev 기준 배포)
-- 대상: RDS  carelog-db.clsg4oyygywj.ap-northeast-2.rds.amazonaws.com / DB=carelog / USER=ah_0301_carelog
-- 적용:  psql "host=<RDS> port=5432 dbname=carelog user=ah_0301_carelog" -f scripts/prod_migration_2026-06-17.sql
-- 모두 idempotent(재실행 안전). 마지막 prod 배포(2026-06-16, app-v1.1.7) 이후 누적 스키마 변경분.
-- aerich 가 구포맷 이슈로 막혀 있어 SQL 직접 적용(프로젝트 관례).
-- ============================================================

BEGIN;

-- (1) 카카오 소셜 로그인 — (provider, social_id) 부분 유니크 인덱스  [migration 30 / PR #267]
CREATE UNIQUE INDEX IF NOT EXISTS "uq_users_social_provider_social_id"
    ON "users" ("social_provider", "social_id")
    WHERE "social_provider" IS NOT NULL AND "social_id" IS NOT NULL;

-- (2) FCM 복약 알림 — users.fcm_token 컬럼
ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(256);

-- (3) FCM 복약 알림 — medication_reminders 테이블 (모델 app/models/medication_reminder.py 와 일치)
CREATE TABLE IF NOT EXISTS medication_reminders (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    medicine_name VARCHAR(100) NOT NULL,
    reminder_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_medrem_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- (4) 챌린지 멤버 신고 — community_reports.target_type 길이 확장  [PR #260]
--     ALTER ... TYPE 는 IF NOT EXISTS 불가하나 동일 타입 재적용은 무해(idempotent).
ALTER TABLE community_reports ALTER COLUMN target_type TYPE VARCHAR(30);

COMMIT;

-- ============================================================
-- [적용 후 검증] — 아래를 실행해 4건이 모두 반영됐는지 확인
-- ============================================================
-- \d+ medication_reminders
-- SELECT column_name, data_type, character_maximum_length
--   FROM information_schema.columns
--   WHERE table_name='users' AND column_name='fcm_token';
-- SELECT character_maximum_length FROM information_schema.columns
--   WHERE table_name='community_reports' AND column_name='target_type';   -- 30 이어야 함
-- SELECT indexname FROM pg_indexes
--   WHERE tablename='users' AND indexname='uq_users_social_provider_social_id';
