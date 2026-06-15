-- Admin system migration

-- 1. community_posts 누락 컬럼 추가
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS info_category VARCHAR(20);
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. support_faqs 테이블 생성
CREATE TABLE IF NOT EXISTS support_faqs (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(20) NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. support_inquiries 테이블 생성
CREATE TABLE IF NOT EXISTS support_inquiries (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(30) NOT NULL,
    attachment_url VARCHAR(512),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. support_inquiry_answers 테이블 생성
CREATE TABLE IF NOT EXISTS support_inquiry_answers (
    id BIGSERIAL PRIMARY KEY,
    inquiry_id BIGINT NOT NULL UNIQUE REFERENCES support_inquiries(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. community_reports 테이블 생성
CREATE TABLE IF NOT EXISTS community_reports (
    id BIGSERIAL PRIMARY KEY,
    target_type VARCHAR(20) NOT NULL,
    target_id BIGINT NOT NULL,
    reason VARCHAR(20) NOT NULL,
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(reporter_id, target_type, target_id)
);
