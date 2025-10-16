-- Migration: Create sync_checkpoints table for tracking historical message sync progress
-- Feature: 004-implement-whatsapp-deep
-- Date: 2025-10-16

CREATE TABLE IF NOT EXISTS sync_checkpoints (
  sync_id TEXT PRIMARY KEY,
  chat_jid TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'interrupted', 'cancelled', 'completed', 'failed')),
  messages_synced INTEGER NOT NULL DEFAULT 0,
  last_message_id TEXT,
  last_timestamp DATETIME,
  progress_percent INTEGER CHECK(progress_percent BETWEEN 0 AND 100),
  error_message TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME
);

-- Index for querying by sync status (e.g., finding interrupted syncs to resume)
CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_status ON sync_checkpoints(status);

-- Index for querying by chat_jid (primary access pattern)
CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_chat_jid ON sync_checkpoints(chat_jid);
