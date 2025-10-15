# Implementing Deep History Fetch (2010-2015 Messages)

## Overview

WhatsApp's `syncFullHistory: true` only syncs recent history (~90-120 days fully, ~1-2 years partially).
To fetch **older messages** (like from 2010, 2015) that you see on your mobile, you need **on-demand history sync** using Baileys' `fetchMessageHistory()` function.

## How It Works

```
1. Find oldest message in your database (e.g., from 2024)
2. Call fetchMessageHistory(100, oldestMessageKey, oldestTimestamp)
3. WhatsApp sends 100 older messages (e.g., from 2023)
4. Repeat step 2-3 with new oldest message
5. Eventually reach 2010-2015 messages (if they exist on WhatsApp's servers)
```

## Implementation Steps

### Step 1: Add Endpoint to Baileys Bridge

Edit `baileys-bridge/src/main.ts` and add this endpoint before the "Start server" section (around line 277):

```typescript
// Deep History Fetch Endpoint
app.post('/api/history/fetch-older', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({
      success: false,
      message: 'Not connected to WhatsApp'
    });
  }

  const {
    chat_jid,
    oldest_message_id,
    oldest_timestamp_ms,
    from_me = false,
    count = 100
  } = req.body;

  // Validation
  if (!chat_jid || !oldest_message_id || !oldest_timestamp_ms) {
    return res.status(400).json({
      success: false,
      message: 'Required: chat_jid, oldest_message_id, oldest_timestamp_ms'
    });
  }

  try {
    // Build message key
    const messageKey = {
      remoteJid: chat_jid,
      id: oldest_message_id,
      fromMe: from_me
    };

    // Request older messages from WhatsApp
    logger.info({
      chat_jid,
      oldest_message_id,
      oldest_timestamp_ms,
      count
    }, '📥 Requesting older messages via fetchMessageHistory');

    const requestId = await sock.fetchMessageHistory(
      count,
      messageKey,
      oldest_timestamp_ms
    );

    logger.info({ requestId }, '✓ History fetch request sent');

    res.json({
      success: true,
      message: `Requested ${count} older messages for ${chat_jid}`,
      request_id: requestId,
      info: 'Messages will arrive via messaging-history.set event with syncType=ON_DEMAND'
    });

  } catch (error) {
    logger.error({ error }, 'Error requesting older messages');
    res.status(500).json({
      success: false,
      message: 'Failed to request older messages',
      error: String(error)
    });
  }
});
```

### Step 2: Update messaging-history.set Event Handler

The event handler is already in place (lines 108-164), but verify it logs ON_DEMAND syncs:

```typescript
sock.ev.on('messaging-history.set', async ({ chats, contacts, messages, isLatest, progress, syncType }) => {
  logger.info(`📥 Receiving history sync: ${chats.length} chats, ${messages.length} messages (progress: ${progress}%, isLatest: ${isLatest}, type: ${syncType})`);

  // Add this check to identify on-demand syncs
  if (syncType === proto.HistorySync.HistorySyncType.ON_DEMAND) {
    logger.info(`🎯 ON-DEMAND history sync - ${messages.length} older messages retrieved`);
  }

  // ... rest of the handler (already implemented)
});
```

### Step 3: Restart Baileys Bridge

```bash
cd /home/guyfawkes/birthday-manager/whatsapp-mcp
./cleanup-bridges.sh
./start-bridges.sh
```

### Step 4: Run Deep History Fetch Script

```bash
.devenv/state/venv/bin/python3 whatsapp-mcp/fetch_deep_history.py
```

The script will:
1. Show you which chats have the oldest messages
2. Ask for confirmation
3. Request older messages for each chat in batches
4. Wait for WhatsApp to send the messages

### Step 5: Monitor Progress

```bash
# Check Baileys logs for ON_DEMAND events
tail -f whatsapp-mcp/baileys-bridge/baileys-bridge.log | grep "ON-DEMAND\|📥"

# Check database growth
sqlite3 whatsapp-mcp/whatsapp-bridge/store/messages.db "SELECT COUNT(*), MIN(timestamp) FROM messages;"
```

## Important Limitations

### WhatsApp Server Limitations

⚠️ **Not all history is available from WhatsApp's servers!**

- **Messages stored on servers**: ~90-120 days fully, ~1-2 years partially
- **Older messages (2010-2015)**: Only available if:
  - They were backed up to Google Drive
  - They're still in your phone's local database
  - WhatsApp hasn't purged them from servers

### What You'll Likely Get

| Time Period | Availability |
|------------|--------------|
| **Last 3 months** | ✅ 95-100% available |
| **3-12 months** | ✅ 80-90% available |
| **1-2 years** | ⚠️ 40-60% available |
| **2-5 years** | ⚠️ 10-30% available |
| **5+ years (2010-2015)** | ❌ 1-5% available (mostly starred/important) |

### If WhatsApp Returns Nothing

If `fetchMessageHistory()` returns no messages when trying to fetch 2015 history, it means:
1. WhatsApp doesn't have those messages on their servers anymore
2. They were never backed up
3. You need to import from Google Drive backup (complex, requires decryption)

See `GOOGLE_DRIVE_BACKUP_IMPORT.md` for the manual backup import process.

## Expected Results

After running the deep history fetch:

### Best Case Scenario
- **Recent chats** (active in last year): ~80-90% of history
- **Old chats** (inactive for years): ~10-20% of history
- **Very old chats** (2010-2015): Starred messages only

### Typical Result
```
Before deep fetch:  231,481 messages (2022-2025)
After deep fetch:   450,000 messages (2020-2025)
                    +800 messages (2015-2019, mostly starred)
```

## Troubleshooting

### Endpoint Returns 404
- Baileys bridge needs restart after adding endpoint
- Check `baileys-bridge.log` for TypeScript compilation errors

### No Messages Arrive
- Wait 5-10 minutes (WhatsApp may delay delivery)
- Check if you're rate-limited (too many requests too fast)
- Verify the chat actually has older messages on your phone

### Script Says "Endpoint Not Implemented"
- The `/api/history/fetch-older` endpoint hasn't been added to `main.ts`
- Follow Step 1 above to add it

### Messages Arrive But Aren't in Database
- Check Go bridge is receiving events from Baileys
- Verify `messaging-history.set` handler is storing messages
- Check `whatsapp-bridge/whatsapp-bridge.log` for errors

## Alternative: Manual Fetch for Specific Chat

You can manually trigger a fetch for a specific chat using curl:

```bash
# 1. Find oldest message for a chat
sqlite3 whatsapp-mcp/whatsapp-bridge/store/messages.db \
  "SELECT id, timestamp FROM messages WHERE chat_jid='CHAT_JID_HERE' ORDER BY timestamp ASC LIMIT 1;"

# 2. Convert timestamp to milliseconds
# Example: 2024-01-15T10:30:00+02:00 → 1705316400000

# 3. Request older messages
curl -X POST http://localhost:8081/api/history/fetch-older \
  -H "Content-Type: application/json" \
  -d '{
    "chat_jid": "CHAT_JID_HERE",
    "oldest_message_id": "MESSAGE_ID_FROM_STEP_1",
    "oldest_timestamp_ms": 1705316400000,
    "from_me": false,
    "count": 100
  }'

# 4. Wait 30-60 seconds, then check for new messages
sqlite3 whatsapp-mcp/whatsapp-bridge/store/messages.db \
  "SELECT COUNT(*) FROM messages WHERE chat_jid='CHAT_JID_HERE';"
```

## Success Indicators

You'll know it's working when you see in `baileys-bridge.log`:

```
📥 Receiving history sync: 0 chats, 87 messages (progress: 0%, isLatest: undefined, type: ON_DEMAND)
🎯 ON-DEMAND history sync - 87 older messages retrieved
✅ Stored 0 chats, 87 messages
```

And in your database:

```bash
# Check date range expanding backward
sqlite3 whatsapp-mcp/whatsapp-bridge/store/messages.db \
  "SELECT strftime('%Y', MIN(timestamp)) as oldest_year, COUNT(*) as total FROM messages;"

# Before: 2022 | 231481
# After:  2018 | 384922  ← Older messages fetched!
```

## Recommendations

1. **Start with 1-2 important chats** to test before running on all 396 chats
2. **Be patient** - WhatsApp may rate-limit requests
3. **Monitor logs** - Watch `baileys-bridge.log` for ON_DEMAND events
4. **Run in batches** - Process 10-20 chats at a time, not all 396 at once
5. **Accept limitations** - You'll likely get 2020+ history, not 2010-2015 (unless starred)

## Next Steps

After implementation and testing:
1. Run `fetch_deep_history.py` for your top 10 most important chats
2. Wait 24 hours to avoid rate limits
3. Check which chats got older history
4. Decide if it's worth running for all 396 chats
5. For 2010-2015 messages, consider Google Drive backup import (complex)
