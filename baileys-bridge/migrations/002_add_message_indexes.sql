-- Migration: Add performance indexes to messages table for efficient history queries
-- Feature: 004-implement-whatsapp-deep
-- Date: 2025-10-16

-- Composite index for finding oldest message in a conversation (critical for cursor pagination)
CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp ON messages(chat_jid, timestamp DESC);

-- Index for deduplication checks (chat_jid + message_id uniqueness)
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_msg ON messages(chat_jid, id);
