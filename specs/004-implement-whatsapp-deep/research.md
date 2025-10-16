# Research: Baileys fetchMessageHistory API Integration

**Date**: 2025-10-16
**Feature**: WhatsApp Historical Message Sync
**Status**: Complete

## Overview

This document captures research findings for implementing WhatsApp deep history fetching using the @whiskeysockets/baileys library's `fetchMessageHistory` API.

## 1. fetchMessageHistory API Pattern

**Decision**: Use asynchronous event-driven pattern with ON_DEMAND history sync

**API Signature**:
```typescript
fetchMessageHistory: (
  count: number,
  oldestMsgKey: WAMessageKey,
  oldestMsgTimestamp: number | Long
) => Promise<string>
```

**Parameters**:
- `count`: Number of messages to fetch (max: 50 per request)
- `oldestMsgKey`: Message key object `{ remoteJid, id, fromMe }`
- `oldestMsgTimestamp`: Unix timestamp in seconds (not milliseconds)

**Return Value**: Promise<string> containing request ID for tracking

**Rationale**: The API is non-blocking and triggers WhatsApp to send messages via the `messaging-history.set` event rather than returning messages directly. This aligns with WhatsApp's asynchronous protocol design.

## 2. Message Key Structure

**Decision**: Construct message keys with three required fields

**Structure**:
```typescript
const messageKey: WAMessageKey = {
  remoteJid: chatJid,      // Chat JID (e.g., "1234567890@s.whatsapp.net")
  id: oldestMessageId,      // Unique message ID from previous batch
  fromMe: false             // Whether message was sent by current user
};
```

**Rationale**: WhatsApp uses these three fields to uniquely identify a message as the starting point for history retrieval. The `participant` field is only needed for group chats.

## 3. Event Handling Pattern

**Decision**: Listen for `messaging-history.set` event with ON_DEMAND filtering

**Implementation Pattern**:
```typescript
sock.ev.on('messaging-history.set', ({ messages, syncType }) => {
  if (syncType === proto.HistorySync.HistorySyncType.ON_DEMAND) {
    // Process on-demand history sync messages
    // Store in database
    // Update checkpoint
  }
});
```

**Rationale**: The `messaging-history.set` event fires for all history syncs (initial, push name, on-demand). Filtering by `syncType === ON_DEMAND` ensures we only process messages from our explicit fetchMessageHistory calls.

## 4. Timestamp Format

**Decision**: Use Unix timestamps in seconds, handle Long type conversion

**Timestamp Handling**:
```typescript
import Long from 'long';

function normalizeTimestamp(ts: number | Long): number {
  return Long.isLong(ts) ? ts.toNumber() : ts;
}

// Convert from JavaScript Date
const timestampSeconds = Math.floor(Date.now() / 1000);
```

**Rationale**: WhatsApp timestamps are stored as Unix timestamps in seconds. The `messageTimestamp` field can be either a JavaScript `number` or a `Long` instance (from protobufjs). Always normalize to number to prevent type errors.

## 5. Rate Limiting Strategy

**Decision**: Implement 3-second delays with exponential backoff on errors

**Rate Limit Configuration**:
- **Delay between requests**: 3000ms (3 seconds)
- **Max messages per request**: 50 (WhatsApp hard limit)
- **Max retries**: 3
- **Backoff strategy**: Exponential (3s → 6s → 12s)

**Rationale**:
- Community testing shows 200ms delays cause message loss
- 3-5 second delays are conservative and safe
- WhatsApp enforces rate limits to prevent abuse
- Exponential backoff handles temporary network issues

## 6. Pagination Strategy

**Decision**: Cursor-based pagination using last message ID and timestamp

**Pagination Pattern**:
```typescript
let cursor: string | undefined = initialMessageId;
let cursorTimestamp: number | undefined = initialTimestamp;

while (totalFetched < maxMessages) {
  const batch = await fetchMessageBatch(sock, chatJid, 50, cursor, cursorTimestamp);

  if (batch.messages.length === 0) break;

  // Update cursor to oldest message in batch
  const oldestMessage = batch.messages[batch.messages.length - 1];
  cursor = oldestMessage.key.id;
  cursorTimestamp = normalizeTimestamp(oldestMessage.messageTimestamp);

  totalFetched += batch.messages.length;
  await delay(3000); // Rate limit
}
```

**Rationale**: Cursor-based pagination is stateful and reliable. Always use the oldest message from the previous batch as the next cursor, tracking both ID and timestamp.

## 7. Error Handling

**Decision**: Classify errors and implement intelligent retry logic

**Error Types**:
- `TIMEOUT`: WhatsApp didn't respond within 30 seconds
- `RATE_LIMIT`: Too many requests, need longer delays
- `DISCONNECTED`: Socket lost connection during request
- `INVALID_KEY`: Message key not found or malformed

**Error Handling Pattern**:
```typescript
try {
  return await sock.fetchMessageHistory(count, messageKey, timestamp);
} catch (error) {
  if (error.message.includes('Timeout')) {
    throw new Error('TIMEOUT: WhatsApp did not respond');
  } else if (error.message.includes('rate limit')) {
    throw new Error('RATE_LIMIT: Too many requests');
  }
  // ... classify other errors
}
```

**Rationale**: Proper error classification enables intelligent retry strategies and helps diagnose production issues.

## 8. Best Practices from Community

**Desktop Browser Emulation**:
```typescript
const sock = makeWASocket({
  browser: Browsers.macOS('Desktop'),
  syncFullHistory: true
});
```
Desktop clients receive more complete history than mobile.

**Message Storage for getMessage Callback**:
```typescript
const sock = makeWASocket({
  getMessage: async (key) => {
    return await database.getMessage(key.id);
  }
});
```
Baileys requires stored messages for certain operations.

**Connection State Monitoring**:
```typescript
sock.ev.on('connection.update', (update) => {
  if (update.connection === 'close') {
    // Pause history sync, save checkpoint
  }
});
```
Monitor connection state to handle disconnections gracefully.

## 9. Complete Implementation Example

**fetchMessageBatch Function**:
```typescript
async function fetchMessageBatch(
  sock: WASocket,
  chatJid: string,
  count: number,
  oldestMessageId: string | undefined,
  oldestTimestamp: number | undefined,
  logger: Logger
): Promise<{ messages: any[]; cursor: string | undefined }> {
  // Validation
  if (!oldestMessageId || !oldestTimestamp) {
    return { messages: [], cursor: undefined };
  }

  // Limit to WhatsApp's max
  const requestCount = Math.min(count, 50);

  // Construct message key
  const messageKey: WAMessageKey = {
    remoteJid: chatJid,
    id: oldestMessageId,
    fromMe: false,
  };

  // Normalize timestamp
  const timestamp = Long.isLong(oldestTimestamp)
    ? oldestTimestamp.toNumber()
    : oldestTimestamp;

  // Request history (non-blocking)
  const requestId = await sock.fetchMessageHistory(
    requestCount,
    messageKey,
    timestamp
  );

  // Wait for messages via event with timeout
  return await waitForHistoryMessages(sock, 30000, logger);
}

function waitForHistoryMessages(
  sock: WASocket,
  timeoutMs: number,
  logger: Logger
): Promise<{ messages: proto.IWebMessageInfo[]; cursor: string | undefined }> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      sock.ev.off('messaging-history.set', handler);
      reject(new Error('Timeout waiting for message history'));
    }, timeoutMs);

    const handler = (event: any) => {
      const { messages, syncType } = event;

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

## 10. Alternatives Considered

**loadMessages() vs fetchMessageHistory()**:
- Rejected: `loadMessages()` only retrieves already-synced messages from local storage
- `fetchMessageHistory()` requests new messages from WhatsApp servers

**Polling vs Event-driven**:
- Rejected polling: Inefficient and doesn't align with Baileys architecture
- Event-driven is the intended pattern

**Synchronous fetching**:
- Not possible: WhatsApp protocol is asynchronous
- Event-based approach is required

## Summary

The implementation requires:
1. Call `sock.fetchMessageHistory()` with proper message key and timestamp
2. Listen for `messaging-history.set` event with `ON_DEMAND` syncType
3. Handle Long type timestamps properly
4. Implement 3-second delays between requests
5. Use cursor-based pagination with last message ID
6. Handle errors with exponential backoff
7. Store messages incrementally with checkpointing

This approach provides reliable, resumable WhatsApp history sync that respects rate limits and handles edge cases.
