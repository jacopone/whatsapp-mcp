# Backend Routing Decision Tree

This guide explains how the Unified MCP Orchestrator routes tool requests to the appropriate backend.

---

## Routing Logic

```
┌─────────────────────────────────────────────────────┐
│          MCP Tool Request from AI Agent             │
└──────────────────────┬──────────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │ Analyze Tool Name   │
            └──────────┬──────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    ┌───▼───┐     ┌────▼────┐    ┌───▼───┐
    │  Go   │     │ Baileys │    │Hybrid │
    │Bridge │     │ Bridge  │    │(Both) │
    └───┬───┘     └────┬────┘    └───┬───┘
        │              │              │
        ▼              ▼              ▼
   56 tools       10 tools        2 tools
```

---

## Go Bridge Tools (56 total)

**When to route to Go**:
- Messaging operations (send, edit, delete, react, forward)
- Contact management (search, profile, status)
- Chat operations (list, archive, pin, mute, mark-as-read)
- Communities (list, get groups, basic mark-as-read)
- Message queries (list, search, context, statistics)
- Privacy settings (block, privacy controls)
- Newsletters (subscribe, create, react)
- Mark-as-read operations (chat-level, message-level)

**Categories handled**:
- **Messaging**: All v2 and legacy messaging tools
- **Contacts**: All contact tools
- **Chats**: All chat management tools
- **Message Query**: All query tools
- **Communities**: list_communities, get_community_groups, mark_community_as_read
- **Privacy**: All privacy tools
- **Newsletters**: All newsletter tools
- **Mark As Read**: mark_as_read, mark_message_read_v2, mark_chat_read_v2

---

## Baileys Bridge Tools (10 total)

**When to route to Baileys**:
- History synchronization operations
- Business catalog queries (Baileys exclusive feature)
- Operations requiring WhatsApp Web advanced features

**Categories handled**:
- **Backend Status**: get_baileys_sync_status
- **History Sync**: retrieve_full_history, fetch_history, cancel_sync, resume_sync, clear_temp_storage, clear_baileys_temp_data
- **Business**: get_business_catalog, get_product_details (BAILEYS EXCLUSIVE)

**Why Baileys for history sync**:
- whatsmeow (Go library) has broken history sync implementation
- Baileys `syncFullHistory` feature works perfectly
- Baileys can retrieve months/years of historical messages

**Why Baileys for business catalogs**:
- whatsmeow doesn't implement WhatsApp Business API catalog features
- Baileys has full support for catalog protocol
- Only option for browsing business product listings

---

## Hybrid Tools (2 total)

**When to use Hybrid**:
- Operations requiring coordination between both bridges
- Complex workflows combining multiple backend capabilities

**Tools**:
1. **backend_status**
   - Checks health of both Go and Baileys bridges
   - Returns combined system status
   - Essential before bulk operations

2. **mark_community_as_read_with_history** (FLAGSHIP)
   - Step 1: Baileys retrieves full history
   - Step 2: Sync messages to Go database
   - Step 3: Go marks all messages as read
   - Step 4: Return unified results
   - Step 5: Cleanup Baileys temp data

3. **sync_history_to_database**
   - Orchestrates Baileys → Go message transfer
   - Implements deduplication logic
   - Syncs checkpoints to Go database

---

## Decision Tree Examples

### Example 1: User wants to send a message
```
Tool: send_text_message_v2()
├─ Check: Is this a messaging operation? YES
├─ Check: Does Go bridge support this? YES
└─ Route to: Go Bridge (port 8080)
```

### Example 2: User wants to browse business catalog
```
Tool: get_business_catalog()
├─ Check: Is this a business catalog operation? YES
├─ Check: Does Go bridge support catalogs? NO
├─ Check: Does Baileys support catalogs? YES
└─ Route to: Baileys Bridge (port 8081)
```

### Example 3: User wants to mark community as read with history
```
Tool: mark_community_as_read_with_history()
├─ Check: Does this require history sync? YES
├─ Check: Does this require mark-as-read? YES
├─ Check: Can single bridge handle both? NO
└─ Route to: Hybrid orchestration
    ├─ Step 1: Baileys Bridge (retrieve_full_history)
    ├─ Step 2: Sync Layer (sync_history_to_database)
    ├─ Step 3: Go Bridge (mark_community_as_read)
    └─ Return: Unified result
```

### Example 4: User wants to check system health
```
Tool: backend_status()
├─ Check: Query Go bridge health? YES
├─ Check: Query Baileys bridge health? YES
├─ Check: Combine results? YES
└─ Route to: Hybrid (both bridges queried in parallel)
```

---

## Routing Implementation

The unified MCP server (`whatsapp-mcp/unified-mcp/main.py`) implements routing logic:

```python
# Simplified routing pseudocode
def route_tool_request(tool_name, params):
    if tool_name in GO_BRIDGE_TOOLS:
        return go_client.execute(tool_name, params)

    elif tool_name in BAILEYS_BRIDGE_TOOLS:
        return baileys_client.execute(tool_name, params)

    elif tool_name in HYBRID_TOOLS:
        return execute_hybrid_workflow(tool_name, params)

    else:
        raise ToolNotFoundError(tool_name)
```

---

## Performance Considerations

**Go Bridge**:
- Fast response times (<100ms for most operations)
- Direct WhatsApp API access
- Recommended for real-time operations

**Baileys Bridge**:
- Slower for history sync (minutes for large histories)
- Temp database overhead
- Use for bulk history retrieval only

**Hybrid Operations**:
- Latency: Sum of both bridge operations
- `mark_community_as_read_with_history`: 2-10 minutes depending on history size
- Use `sync_timeout` parameter to control maximum wait time

---

## Troubleshooting Routing Issues

**Problem**: Tool returns `BRIDGE_UNREACHABLE` error

**Diagnosis**:
1. Check which backend the tool uses (see category badge in API docs)
2. Verify that backend is running:
   - Go: `curl http://localhost:8080/health`
   - Baileys: `curl http://localhost:8081/health`
3. Check `backend_status()` for overall system health

**Problem**: Hybrid tool times out

**Solution**:
- Increase `sync_timeout` parameter
- Check both bridges are operational
- Verify network connectivity
- Monitor with `get_baileys_sync_status()` during operation

---

## Tool Count by Backend

| Backend | Tool Count | Percentage |
|---------|------------|------------|
| Go Bridge | 56 | 74.7% |
| Baileys Bridge | 10 | 13.3% |
| Hybrid | 2 | 2.7% |
| Miscellaneous | 7 | 9.3% |
| **Total** | **75** | **100%** |
