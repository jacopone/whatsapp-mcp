-- Migration: 003_add_sync_checkpoints.sql
-- Purpose: Create sync_checkpoints table for history sync resume capability
-- Date: 2025-10-10
-- Dependencies: 002_add_message_metadata.sql
-- Features: EC-1.1 through EC-1.5 (History Sync with Checkpoints)

CREATE TABLE IF NOT EXISTS sync_checkpoints (
  -- Primary Key
  chat_jid TEXT PRIMARY KEY NOT NULL,

  -- Checkpoint State
  last_message_id TEXT,            -- Last successfully synced message ID
  last_timestamp INTEGER,          -- Timestamp of last synced message
  messages_synced INTEGER NOT NULL DEFAULT 0,
  total_estimated INTEGER,         -- Estimated total messages (if known)

  -- Status Tracking
  status TEXT NOT NULL DEFAULT 'not_started',
    -- Values: 'not_started', 'in_progress', 'completed', 'interrupted', 'failed', 'cancelled'

  error_message TEXT,              -- Error details if failed

  -- Timestamps
  started_at INTEGER,              -- When sync began
  updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
  completed_at INTEGER,            -- When sync completed (NULL if incomplete)

  -- Foreign Keys
  FOREIGN KEY (chat_jid) REFERENCES chats(jid) ON DELETE CASCADE,

  -- Constraints
  CHECK (status IN ('not_started', 'in_progress', 'completed', 'interrupted', 'failed', 'cancelled'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON sync_checkpoints(status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_updated ON sync_checkpoints(updated_at DESC);

-- Migration metadata
INSERT INTO schema_migrations (version, applied_at) VALUES ('003', strftime('%s', 'now'));
