-- Migration: 002_add_message_metadata.sql
-- Purpose: Create messages table with support for polls, status, reactions, and media
-- Date: 2025-10-10
-- Dependencies: 001_add_community_support.sql
-- Features: FR-3 (Polls), FR-4 (Status), FR-10 (Reactions), FR-11 (Media), FR-14 (Read Receipts)

CREATE TABLE IF NOT EXISTS messages (
  -- Identity
  id TEXT NOT NULL,                -- Message ID from WhatsApp
  chat_jid TEXT NOT NULL,          -- Chat this message belongs to
  timestamp INTEGER NOT NULL,      -- Unix timestamp (seconds)

  -- Sender Information
  sender TEXT NOT NULL,            -- Sender JID (user or group participant)
  from_me BOOLEAN DEFAULT 0,       -- Sent by this account

  -- Content
  content TEXT,                    -- Text content (NULL for media-only)
  message_type TEXT DEFAULT 'text', -- Message type: 'text', 'poll', 'status', 'image', 'video', etc.

  -- Extended Metadata (JSON columns for flexibility)
  poll_data TEXT,                  -- JSON poll structure (FR-3)
  media_url TEXT,                  -- Media URL or local path (FR-4, FR-11)
  reactions TEXT,                  -- JSON array of reactions (FR-10)
  quoted_message_id TEXT,          -- ID of quoted/replied message

  -- Sync Tracking
  sync_source TEXT DEFAULT 'go',   -- Origin backend: 'go' or 'baileys'

  -- Timestamps
  created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),

  -- Constraints
  PRIMARY KEY (chat_jid, timestamp, id),
  FOREIGN KEY (chat_jid) REFERENCES chats(jid) ON DELETE CASCADE
);

-- Indexes for performance (target: < 100ms queries)
CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp ON messages(chat_jid, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_sync_source ON messages(sync_source);

-- Migration metadata
INSERT INTO schema_migrations (version, applied_at) VALUES ('002', strftime('%s', 'now'));
