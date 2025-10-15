-- Migration: 000_create_migrations_table.sql
-- Purpose: Create migration tracking table to record applied database migrations
-- Date: 2025-10-10
-- Dependencies: None (must run first)

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY NOT NULL,
  applied_at INTEGER NOT NULL
);

-- Record this migration
INSERT INTO schema_migrations (version, applied_at) VALUES ('000', strftime('%s', 'now'));
