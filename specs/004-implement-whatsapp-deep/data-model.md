# Data Model: WhatsApp Historical Message Sync

**Date**: 2025-10-16
**Feature**: 004-implement-whatsapp-deep
**Status**: Complete

## Overview

This document defines the data entities and their relationships for the WhatsApp historical message sync feature. The model builds on existing database structures in baileys-bridge.

## Core Entities

### 1. Historical Message

**Purpose**: Represents a WhatsApp message retrieved via on-demand history sync

**Attributes**:
- `id` (string, required): Unique WhatsApp message ID
- `chat_jid` (string, required, indexed): Conversation identifier (e.g., "1234567890@s.whatsapp.net")
- `sender` (string, required): JID of message sender (or "me" for outgoing)
- `content` (text, required): Message text content or media description
- `timestamp` (datetime, required, indexed): Message sent time (UTC)
- `is_from_me` (boolean, required): True if sent by current user
- `message_type` (string, optional): Type (text, image, video, document, etc.)
- `raw_proto` (json, optional): Full protobuf message for advanced processing

**Relationships**:
- Belongs to one Sync Checkpoint (via chat_jid)
- Part of one Conversation (via chat_jid)

**Validation Rules**:
- `id` must be unique per chat_jid
- `timestamp` must be in valid date range (2010-present)
- `chat_jid` must match WhatsApp JID format (@s.whatsapp.net or @g.us)

**State Transitions**: N/A (immutable once stored)

### 2. Sync Checkpoint

**Purpose**: Tracks progress and state of historical message sync for a conversation

**Attributes**:
- `sync_id` (string, required, primary key): Unique sync identifier (use chat_jid)
- `chat_jid` (string, required, unique): Conversation being synced
- `status` (enum, required): Current sync state
  - `not_started`: Initial state
  - `in_progress`: Actively fetching messages
  - `interrupted`: Stopped mid-sync (resumable)
  - `cancelled`: User-cancelled (resumable)
  - `completed`: Successfully fetched all available messages
  - `failed`: Encountered unrecoverable error
- `messages_synced` (integer, required, default: 0): Total messages fetched so far
- `last_message_id` (string, nullable): ID of oldest message fetched (cursor)
- `last_timestamp` (datetime, nullable): Timestamp of oldest message (cursor)
- `progress_percent` (integer, nullable): Completion percentage (0-100)
- `error_message` (text, nullable): Error details if status is failed
- `created_at` (datetime, required): When sync started
- `updated_at` (datetime, required): Last checkpoint update
- `completed_at` (datetime, nullable): When sync finished

**Relationships**:
- Has many Historical Messages (via chat_jid)

**Validation Rules**:
- `status` must be one of defined enum values
- `progress_percent` must be 0-100
- `messages_synced` must be non-negative
- If `status` is completed, `completed_at` must be set
- If `last_message_id` is set, `last_timestamp` must also be set

**State Transitions**:
```
not_started → in_progress
in_progress → completed | interrupted | cancelled | failed
interrupted → in_progress
cancelled → in_progress
failed → (end state, cannot resume)
completed → (end state)
```

### 3. Sync Request

**Purpose**: Represents a user/system request to sync historical messages

**Attributes**:
- `request_id` (string, required, primary key): Unique request identifier
- `chat_jid` (string, required): Target conversation
- `max_messages` (integer, required): Maximum messages to fetch
- `resume` (boolean, required, default: false): Whether to resume from checkpoint
- `requested_at` (datetime, required): When request was made
- `requested_by` (string, optional): User or system component that initiated

**Relationships**:
- May create one Sync Checkpoint

**Validation Rules**:
- `max_messages` must be between 1 and 10,000
- `chat_jid` must be valid WhatsApp JID format

**State Transitions**: Immutable (request records are historical)

### 4. Sync Status (Global)

**Purpose**: Tracks system-wide sync state for database coordination

**Attributes**:
- `id` (integer, primary key): Always 1 (singleton)
- `is_syncing` (boolean, required): Whether any sync is active
- `messages_synced` (integer, required, default: 0): Total messages across all syncs
- `last_sync_time` (datetime, nullable): Most recent sync activity
- `progress_percent` (integer, nullable): Overall progress across active syncs
- `is_latest` (boolean, required, default: false): Whether all available messages are synced

**Relationships**:
- None (global singleton)

**Validation Rules**:
- Only one row allowed (id=1)
- `progress_percent` must be 0-100

**State Transitions**:
- `is_syncing` toggles true/false as syncs start/stop
- `is_latest` set to true when all conversations reach completion

## Entity Relationships

```
┌─────────────────────┐
│   Sync Request      │
│   (User initiated)  │
└──────────┬──────────┘
           │ creates
           ▼
┌─────────────────────┐      1:N      ┌─────────────────────┐
│  Sync Checkpoint    │───────────────▶│  Historical Message │
│  (Progress tracker) │                │  (WhatsApp messages)│
└─────────────────────┘                └─────────────────────┘
           │
           │ updates
           ▼
┌─────────────────────┐
│    Sync Status      │
│  (Global singleton) │
└─────────────────────┘
```

## Storage Considerations

### Database Schema

**messages table** (existing, enhanced):
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  chat_jid TEXT NOT NULL,
  sender TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp DATETIME NOT NULL,
  is_from_me BOOLEAN NOT NULL DEFAULT 0,
  message_type TEXT,
  raw_proto JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_chat_jid ON messages(chat_jid);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE UNIQUE INDEX idx_messages_chat_msg ON messages(chat_jid, id);
```

**sync_checkpoints table** (new):
```sql
CREATE TABLE sync_checkpoints (
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

CREATE INDEX idx_sync_checkpoints_status ON sync_checkpoints(status);
CREATE INDEX idx_sync_checkpoints_chat_jid ON sync_checkpoints(chat_jid);
```

**sync_status table** (existing):
```sql
CREATE TABLE sync_status (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  is_syncing BOOLEAN NOT NULL DEFAULT 0,
  messages_synced INTEGER NOT NULL DEFAULT 0,
  last_sync_time DATETIME,
  progress_percent INTEGER CHECK(progress_percent BETWEEN 0 AND 100),
  is_latest BOOLEAN NOT NULL DEFAULT 0
);

-- Initialize singleton row
INSERT INTO sync_status (id, is_syncing, messages_synced, is_latest)
VALUES (1, 0, 0, 0);
```

### Indexing Strategy

**Query Patterns**:
1. **Get messages for chat**: `SELECT * FROM messages WHERE chat_jid = ? ORDER BY timestamp DESC`
   - Index: `idx_messages_chat_jid`, `idx_messages_timestamp`

2. **Find oldest message**: `SELECT id, timestamp FROM messages WHERE chat_jid = ? ORDER BY timestamp ASC LIMIT 1`
   - Index: `idx_messages_chat_msg` (composite)

3. **Check sync status**: `SELECT * FROM sync_checkpoints WHERE chat_jid = ?`
   - Index: `idx_sync_checkpoints_chat_jid`

4. **Resume interrupted syncs**: `SELECT * FROM sync_checkpoints WHERE status IN ('interrupted', 'cancelled')`
   - Index: `idx_sync_checkpoints_status`

### Data Volume Estimates

**Assumptions**:
- Average conversation: 5,000 messages over 2 years
- 50 important conversations
- Message size: ~500 bytes average

**Storage Requirements**:
- Messages: 50 conversations × 5,000 msgs × 500 bytes = ~125 MB
- Checkpoints: 50 conversations × 1 KB = 50 KB
- Total: ~125 MB (conservative estimate)

## Data Integrity Rules

### Deduplication

**Rule**: Messages with same `chat_jid` + `id` are duplicates

**Enforcement**: Unique index `idx_messages_chat_msg` prevents duplicates at database level

**Handling Strategy**:
```sql
INSERT OR IGNORE INTO messages (id, chat_jid, ...) VALUES (...);
```

### Checkpoint Consistency

**Rule**: Checkpoint `last_message_id` must exist in messages table

**Enforcement**: Application-level validation before updating checkpoint

**Validation**:
```typescript
const messageExists = await database.messageExists(chat_jid, message_id);
if (!messageExists) {
  throw new Error('Cannot set checkpoint to non-existent message');
}
```

### Timestamp Monotonicity

**Rule**: Each batch should have `timestamp` ≤ previous batch's oldest timestamp

**Enforcement**: Application-level warning (not strict error, due to timestamp edge cases)

**Validation**:
```typescript
if (batchOldestTimestamp > checkpointLastTimestamp) {
  logger.warn('Timestamp ordering violation - possible WhatsApp timestamp inconsistency');
}
```

## Migration Considerations

### Existing Data

The `baileys-bridge` database already has:
- `messages` table with basic fields
- `sync_status` singleton table

**Required Migrations**:
1. Add `message_type` and `raw_proto` columns to `messages` (optional)
2. Create `sync_checkpoints` table
3. Add indexes for efficient queries

**Backward Compatibility**:
- Existing messages remain valid
- New sync populates checkpoints for tracking
- Legacy queries continue to work

## Summary

The data model supports:
- Efficient storage of historical messages
- Resumable sync with checkpoint tracking
- Progress monitoring and error recovery
- Deduplication via unique indexes
- Scalable to hundreds of thousands of messages

Key design decisions:
- Use `chat_jid` as natural sync identifier
- Store full message history (not just metadata)
- Checkpoint-based resumability
- Status tracking at both conversation and system level
