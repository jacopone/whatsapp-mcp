# Quick Start: WhatsApp Deep History Sync

**Feature**: 004-implement-whatsapp-deep
**Date**: 2025-10-16
**Audience**: Developers implementing or testing the historical message sync feature

## Overview

This guide helps you quickly get started with implementing and testing WhatsApp deep history synchronization using the Baileys bridge.

## Prerequisites

- WhatsApp MCP server running (`~/whatsapp-mcp`)
- Baileys bridge connected to WhatsApp
- Node.js 20+ and TypeScript 5+
- SQLite database initialized
- QR code authentication completed

## Quick Test (5 minutes)

### 1. Start the Baileys Bridge

```bash
cd ~/whatsapp-mcp/baileys-bridge
npm run dev
```

Bridge should start on `http://localhost:8081`

### 2. Verify WhatsApp Connection

```bash
curl http://localhost:8081/health
```

Expected response:
```json
{
  "status": "connected",
  "uptime": 123
}
```

###

 3. Start History Sync for a Chat

```bash
curl -X POST http://localhost:8081/history/sync \
  -H "Content-Type: application/json" \
  -d '{
    "chat_jid": "1234567890@s.whatsapp.net",
    "max_messages": 1000
  }'
```

Expected response (202 Accepted):
```json
{
  "sync_id": "1234567890@s.whatsapp.net",
  "checkpoint": {
    "chat_jid": "1234567890@s.whatsapp.net",
    "status": "in_progress",
    "messages_synced": 0,
    "progress_percent": 0
  },
  "status": "started"
}
```

### 4. Monitor Sync Progress

```bash
curl http://localhost:8081/history/sync/1234567890@s.whatsapp.net/status
```

Expected response:
```json
{
  "checkpoint": {
    "chat_jid": "1234567890@s.whatsapp.net",
    "status": "in_progress",
    "messages_synced": 250,
    "progress_percent": 25
  },
  "is_active": true
}
```

### 5. Query Synced Messages

```bash
curl "http://localhost:8081/history/messages?chat_jid=1234567890@s.whatsapp.net&limit=10"
```

Expected response:
```json
{
  "chat_jid": "1234567890@s.whatsapp.net",
  "count": 10,
  "messages": [
    {
      "id": "MSG_123",
      "sender": "1234567890@s.whatsapp.net",
      "content": "Hello!",
      "timestamp": "2023-08-15T14:30:00Z",
      "is_from_me": false
    }
  ]
}
```

## Development Workflow

### Setting Up Development Environment

1. **Clone and install dependencies**:
```bash
cd ~/whatsapp-mcp/baileys-bridge
npm install
```

2. **Build TypeScript**:
```bash
npm run build
```

3. **Run tests**:
```bash
npm test
```

### Key Files to Modify

**1. `/src/routes/history.ts`** (lines 443-491)
- Implement `fetchMessageBatch()` function
- Add Baileys `fetchMessageHistory()` call
- Handle `messaging-history.set` event

**2. `/src/services/baileys_client.ts`**
- Ensure socket event handlers are registered
- Add ON_DEMAND history sync event listener

**3. `/src/services/database.ts`**
- Verify message storage functions
- Ensure checkpoint persistence

### Implementation Checklist

- [ ] Import necessary Baileys types (`WASocket`, `WAMessageKey`, `proto`)
- [ ] Import `Long` type for timestamp handling
- [ ] Implement `fetchMessageHistory()` API call
- [ ] Add `messaging-history.set` event listener with ON_DEMAND filter
- [ ] Handle Long timestamp conversion
- [ ] Implement 3-second rate limiting delays
- [ ] Add error handling with exponential backoff
- [ ] Test with a single conversation
- [ ] Test resume functionality
- [ ] Test cancellation
- [ ] Verify deduplication works

### Code Template

Here's a minimal implementation template for `fetchMessageBatch()`:

```typescript
import { WASocket, WAMessageKey, proto } from '@whiskeysockets/baileys';
import Long from 'long';

async function fetchMessageBatch(
  sock: WASocket,
  chatJid: string,
  count: number,
  oldestMessageId: string | undefined,
  logger: Logger
): Promise<{ messages: any[]; cursor: string | undefined }> {
  // TODO: Get oldest message timestamp from database
  const oldestMessage = await database.getOldestMessage(chatJid);
  if (!oldestMessage) {
    return { messages: [], cursor: undefined };
  }

  // Construct message key
  const messageKey: WAMessageKey = {
    remoteJid: chatJid,
    id: oldestMessage.id,
    fromMe: oldestMessage.is_from_me
  };

  // Normalize timestamp
  const timestamp = normalizeTimestamp(oldestMessage.timestamp);

  // Request history
  await sock.fetchMessageHistory(
    Math.min(count, 50),
    messageKey,
    timestamp
  );

  // Wait for messages via event
  return await waitForHistoryMessages(sock, 30000);
}

function normalizeTimestamp(ts: Date | number | Long): number {
  if (ts instanceof Date) {
    return Math.floor(ts.getTime() / 1000);
  }
  return Long.isLong(ts) ? ts.toNumber() : ts;
}

function waitForHistoryMessages(
  sock: WASocket,
  timeoutMs: number
): Promise<{ messages: any[]; cursor: string | undefined }> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      sock.ev.off('messaging-history.set', handler);
      reject(new Error('Timeout'));
    }, timeoutMs);

    const handler = ({ messages, syncType }) => {
      if (syncType === proto.HistorySync.HistorySyncType.ON_DEMAND) {
        clearTimeout(timeout);
        sock.ev.off('messaging-history.set', handler);

        const cursor = messages.length > 0
          ? messages[messages.length - 1].key.id
          : undefined;

        resolve({ messages, cursor });
      }
    };

    sock.ev.on('messaging-history.set', handler);
  });
}
```

## Testing

### Unit Tests

Create `tests/history.test.ts`:

```typescript
import { describe, it, expect, jest } from '@jest/globals';
import { fetchMessageBatch } from '../src/routes/history';

describe('fetchMessageBatch', () => {
  it('should fetch messages with valid cursor', async () => {
    const mockSock = {
      fetchMessageHistory: jest.fn().mockResolvedValue('request_id'),
      ev: {
        on: jest.fn(),
        off: jest.fn()
      }
    };

    const result = await fetchMessageBatch(
      mockSock as any,
      '1234567890@s.whatsapp.net',
      50,
      'MSG_123',
      mockLogger
    );

    expect(mockSock.fetchMessageHistory).toHaveBeenCalled();
    expect(result.messages).toBeDefined();
  });
});
```

Run tests:
```bash
npm test
```

### Integration Tests

Test with actual WhatsApp connection:

```bash
# Start bridge
npm run dev

# In another terminal, run integration test
curl -X POST http://localhost:8081/history/sync \
  -H "Content-Type: application/json" \
  -d '{
    "chat_jid": "<your-contact-jid>",
    "max_messages": 100
  }'

# Monitor logs
tail -f logs/baileys-bridge.log
```

### Manual Testing Scenarios

1. **Happy Path**: Sync completes successfully
2. **Resume**: Interrupt sync (Ctrl+C), restart, resume
3. **Cancel**: Start sync, cancel mid-process
4. **Rate Limit**: Request multiple syncs simultaneously
5. **Invalid JID**: Test error handling with malformed JID
6. **Disconnection**: Disconnect WhatsApp during sync

## Debugging

### Enable Debug Logging

Edit `src/main.ts`:
```typescript
const logger = pino({ level: 'debug' });
```

### Check Database State

```bash
sqlite3 ~/whatsapp-mcp/baileys-bridge/store/messages.db

# Check sync status
SELECT * FROM sync_checkpoints;

# Check message count
SELECT chat_jid, COUNT(*) as count
FROM messages
GROUP BY chat_jid
ORDER BY count DESC
LIMIT 10;

# Check oldest message
SELECT id, timestamp
FROM messages
WHERE chat_jid = '1234567890@s.whatsapp.net'
ORDER BY timestamp ASC
LIMIT 1;
```

### Common Issues

**Issue**: "Timeout waiting for message history"
- **Cause**: WhatsApp didn't respond within 30 seconds
- **Solution**: Check network connection, increase timeout

**Issue**: "WhatsApp is not connected"
- **Cause**: Socket disconnected
- **Solution**: Restart bridge, re-authenticate with QR code

**Issue**: "Rate limit exceeded"
- **Cause**: Too many requests too quickly
- **Solution**: Increase delay between requests (>3 seconds)

**Issue**: "Cannot find message with ID"
- **Cause**: Cursor message doesn't exist in database
- **Solution**: Query for oldest message before starting sync

## Performance Optimization

### Batch Size Tuning

```typescript
// Conservative (slower, more reliable)
const BATCH_SIZE = 25;
const DELAY_MS = 5000;

// Aggressive (faster, may hit rate limits)
const BATCH_SIZE = 50;
const DELAY_MS = 2000;
```

### Database Indexing

Ensure indexes exist:
```sql
CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp
ON messages(chat_jid, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_status
ON sync_checkpoints(status);
```

### Connection Pooling

For high-volume sync:
```typescript
// Increase SQLite connection pool
const db = new Database({
  maxConnections: 10,
  busyTimeout: 5000
});
```

## Next Steps

1. **Read the full spec**: `specs/004-implement-whatsapp-deep/spec.md`
2. **Review data model**: `specs/004-implement-whatsapp-deep/data-model.md`
3. **Check API contract**: `specs/004-implement-whatsapp-deep/contracts/history-sync-api.yaml`
4. **Study research findings**: `specs/004-implement-whatsapp-deep/research.md`
5. **Implement fetchMessageBatch**: Modify `src/routes/history.ts`
6. **Run tests**: Verify functionality
7. **Deploy**: Test with production WhatsApp account

## Support

- **Repository**: `~/whatsapp-mcp`
- **Documentation**: `specs/004-implement-whatsapp-deep/`
- **Existing code**: `baileys-bridge/src/routes/history.ts` (scaffold already exists)

## Summary

This quickstart covered:
- ✅ Quick 5-minute test procedure
- ✅ Development environment setup
- ✅ Key files and implementation checklist
- ✅ Code templates and examples
- ✅ Testing strategies
- ✅ Debugging techniques
- ✅ Performance optimization

You should now be able to implement and test the WhatsApp deep history sync feature!
