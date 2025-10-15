-- Migration: 001_add_community_support.sql
-- Purpose: Create chats table with community, broadcast, and newsletter support
-- Date: 2025-10-10
-- Dependencies: 000_create_migrations_table.sql
-- Features: FR-5 (Broadcast), FR-7 (Communities), FR-8 (Newsletters)

CREATE TABLE IF NOT EXISTS chats (
  -- Primary Key
  jid TEXT PRIMARY KEY NOT NULL,  -- WhatsApp JID (e.g., "1234567890@s.whatsapp.net")

  -- Core Metadata
  name TEXT,                       -- Display name
  is_group BOOLEAN DEFAULT 0,      -- Individual vs group chat
  is_community BOOLEAN DEFAULT 0,  -- Community flag (FR-7)
  is_broadcast BOOLEAN DEFAULT 0,  -- Broadcast list flag (FR-5)
  is_newsletter BOOLEAN DEFAULT 0, -- Newsletter channel flag (FR-8)

  -- Community Relationships
  parent_group_jid TEXT,           -- Parent community JID (FR-7)

  -- Timestamps
  created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
  updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),

  -- Optional Metadata
  avatar_url TEXT,
  description TEXT,
  participant_count INTEGER,
  unread_count INTEGER DEFAULT 0,

  -- Foreign Keys
  FOREIGN KEY (parent_group_jid) REFERENCES chats(jid) ON DELETE SET NULL
);

-- Indexes for performance (target: < 100ms queries)
CREATE INDEX IF NOT EXISTS idx_chats_parent_community ON chats(parent_group_jid) WHERE parent_group_jid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chats_is_community ON chats(is_community) WHERE is_community = 1;
CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats(updated_at DESC);

-- Migration metadata
INSERT INTO schema_migrations (version, applied_at) VALUES ('001', strftime('%s', 'now'));
