-- Admin system migration
-- Adds soft-delete columns to community_posts and support_faqs

ALTER TABLE community_posts
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE support_faqs
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
