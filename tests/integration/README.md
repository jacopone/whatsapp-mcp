# Integration Tests for WhatsApp MCP

Integration tests for Phase 3 (User Story 1.2: Message Query Tools).

## Prerequisites

Before running the tests, ensure:

1. **Go Backend is running** on `http://localhost:8080`
   ```bash
   cd whatsapp-mcp/whatsapp-bridge
   ./whatsapp-bridge
   ```

2. **Database has messages synced**
   - Either sync history from Baileys
   - Or have real-time messages collected

## Running the Tests

### Test Message Query Endpoints (T024-T026)

This test suite validates:
- T024: Go REST API endpoints for querying messages
- T025: Python MCP tools that call these endpoints
- T026: Full end-to-end integration

```bash
# From project root
cd whatsapp-mcp/tests/integration
python test_message_query.py
```

### What the Tests Cover

1. **Backend Health**: Verify Go backend is accessible
2. **Message Statistics**: Test `/api/stats` endpoint
3. **Query All Messages**: Test basic message query with pagination
4. **Query by Chat**: Filter messages by specific chat JID
5. **Search by Content**: Full-text search in message content
6. **Pagination**: Verify offset/limit pagination works correctly
7. **Media Filtering**: Test include_media and media_type filters

### Expected Output

Successful test run:
```
================================================================================
INTEGRATION TEST SUITE: Message Query Endpoints (T026)
================================================================================

TEST 1: Backend Health Check
✅ Go backend healthy: True

TEST 2: Get Message Statistics
✅ Statistics retrieved successfully:
   Total messages: 1523
   Total chats: 45
   ...

...

================================================================================
TEST SUMMARY
================================================================================
✅ PASS: Backend Health
✅ PASS: Message Statistics
✅ PASS: Query All Messages
✅ PASS: Query by Chat
✅ PASS: Search by Content
✅ PASS: Pagination
✅ PASS: Media Filtering

Total: 7/7 tests passed

🎉 ALL TESTS PASSED! 🎉
```

## Troubleshooting

### "Go backend is not healthy"
- Make sure whatsapp-bridge is running
- Check it's listening on port 8080
- Verify with: `curl http://localhost:8080/health`

### "No messages available to test with"
- The database needs messages before testing queries
- Run history sync or wait for real-time messages
- Check database: `sqlite3 whatsapp-mcp/whatsapp-bridge/store/messages.db "SELECT COUNT(*) FROM messages;"`

### Import errors
- Make sure you're running from the project root
- Ensure dependencies are installed: `pip install requests`

## Manual Testing

You can also test the endpoints manually:

```bash
# Get statistics
curl http://localhost:8080/api/stats

# Query all messages
curl "http://localhost:8080/api/messages?limit=10"

# Search by content
curl "http://localhost:8080/api/messages?content=hello&limit=10"

# Filter by chat
curl "http://localhost:8080/api/messages?chat_jid=123456789@g.us&limit=20"

# Query with time range (ISO 8601 format)
curl "http://localhost:8080/api/messages?after_time=2025-01-01T00:00:00Z&limit=50"

# Include media messages
curl "http://localhost:8080/api/messages?include_media=true&limit=10"

# Filter by media type
curl "http://localhost:8080/api/messages?include_media=true&media_type=image&limit=10"
```

## Test Data Requirements

For comprehensive testing, your database should have:
- Multiple chats
- Messages with different content
- Both text and media messages
- Messages from different time periods

You can populate the database by:
1. Running the Baileys history sync
2. Letting the Go backend collect real-time messages
3. Or both
