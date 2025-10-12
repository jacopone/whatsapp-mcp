# Hybrid Operations Examples

This guide explains how to work with hybrid operations that combine both Go and Baileys bridges for advanced functionality.

---

## Understanding the Hybrid Architecture

**Three-Layer System**:
```
┌─────────────────────────────────────────────────────────────┐
│                   Unified MCP Orchestrator                   │
│                    (Python - Port 3000)                      │
└───────────────┬──────────────────────────┬──────────────────┘
                │                          │
    ┌───────────▼──────────┐   ┌──────────▼──────────┐
    │   Go Bridge (8080)   │   │ Baileys Bridge      │
    │   whatsmeow library  │   │   (8081)            │
    │   - Messaging        │   │ - History sync      │
    │   - Communities      │   │ - Business catalogs │
    │   - Mark as read     │   │ - Advanced features │
    └──────────────────────┘   └─────────────────────┘
```

**Why Hybrid?**
- whatsmeow (Go): Fast, reliable messaging but broken history sync
- Baileys (Node.js): Full history sync works perfectly, business features
- Combining both: 95%+ WhatsApp feature coverage

---

## Example 1: Full History Retrieval (Baileys)

```python
# Retrieve ALL historical messages using Baileys
print("Starting full history retrieval...")
print("This is a ONE-TIME operation - may take 5-20 minutes")

result = retrieve_full_history(
    wait_for_completion=True,
    timeout=1200  # 20 minutes max
)

if result["success"]:
    print(f"✅ History sync complete!")
    print(f"Messages synced: {result['messages_synced']}")
    print(f"Duration: {result['sync_duration_seconds']}s")
    print(f"Status: {result['status']}")
else:
    print(f"❌ Failed: {result['message']}")
```

**When to use**:
- First time setup after authentication
- You haven't used WhatsApp MCP for weeks/months
- Want to search/analyze historical conversations

**How it works**:
1. Baileys calls WhatsApp's `syncFullHistory` API
2. Downloads all messages to Baileys temp database
3. Returns completion status
4. Messages ready for `sync_history_to_database()`

---

## Example 2: Sync Messages to Go Database

```python
# Transfer messages from Baileys temp DB → Go permanent database
print("Syncing messages to Go database...")

result = sync_history_to_database()

if result["success"]:
    print(f"✅ Sync complete!")
    print(f"Messages synced: {result['messages_synced']}")
    print(f"Duplicates skipped: {result['duplicates_skipped']}")
    print(f"Failed: {result['failed']}")
else:
    print(f"❌ Failed: {result['message']}")
```

**When to use**: After `retrieve_full_history()` to make messages searchable and mark-as-read-able.

**How it works**:
1. Reads all messages from Baileys SQLite temp DB
2. Inserts into Go messages.db with deduplication
3. Uses composite key (chat_jid + message_id + timestamp)
4. Syncs checkpoints for resume capability

---

## Example 3: Complete History Setup (Baileys → Go Pipeline)

```python
# Full pipeline: Retrieve → Sync → Verify
def setup_full_history():
    """One-time setup to download and sync all WhatsApp history."""

    print("🚀 Starting complete history setup...")
    print("=" * 60)

    # Step 1: Check backend health
    print("\n[1/4] Checking backend health...")
    health = backend_status()

    if health["overall_status"] != "healthy":
        print("❌ Backends not healthy. Aborting.")
        print(f"Go: {health['go_bridge']['healthy']}")
        print(f"Baileys: {health['baileys_bridge']['healthy']}")
        return
    print("✅ Backends healthy")

    # Step 2: Retrieve full history via Baileys
    print("\n[2/4] Retrieving full history (this may take 10-20 minutes)...")
    history_result = retrieve_full_history(
        wait_for_completion=True,
        timeout=1200  # 20 minutes
    )

    if not history_result["success"]:
        print(f"❌ History retrieval failed: {history_result['message']}")
        return

    print(f"✅ Retrieved {history_result['messages_synced']} messages")

    # Step 3: Sync to Go database
    print("\n[3/4] Syncing messages to Go database...")
    sync_result = sync_history_to_database()

    if not sync_result["success"]:
        print(f"❌ Database sync failed: {sync_result['message']}")
        return

    print(f"✅ Synced {sync_result['messages_synced']} messages")
    print(f"   Duplicates skipped: {sync_result['duplicates_skipped']}")

    # Step 4: Verify with statistics
    print("\n[4/4] Verifying message statistics...")
    stats = get_message_statistics()

    print(f"✅ Database now contains:")
    print(f"   Total messages: {stats['total_messages']}")
    print(f"   Total chats: {stats['total_chats']}")
    print(f"   Media messages: {stats['media_messages']}")
    print(f"   Text messages: {stats['text_messages']}")

    print("\n" + "=" * 60)
    print("🎉 History setup complete!")
    print("You can now:")
    print("  - Search messages with query_synced_messages()")
    print("  - Mark communities as read with mark_community_as_read_with_history()")
    print("  - Analyze message statistics")

# Run setup
setup_full_history()
```

**Expected output**:
```
🚀 Starting complete history setup...
============================================================

[1/4] Checking backend health...
✅ Backends healthy

[2/4] Retrieving full history (this may take 10-20 minutes)...
✅ Retrieved 8432 messages

[3/4] Syncing messages to Go database...
✅ Synced 8432 messages
   Duplicates skipped: 0

[4/4] Verifying message statistics...
✅ Database now contains:
   Total messages: 8432
   Total chats: 67
   Media messages: 2145
   Text messages: 6287

============================================================
🎉 History setup complete!
```

---

## Example 4: Incremental History Sync for Specific Chat

```python
# Sync history for a single chat (more targeted than full sync)
chat_jid = "1234567890@s.whatsapp.net"

print(f"Syncing history for {chat_jid}...")

# Fetch history for specific chat
fetch_result = fetch_history(
    chat_jid=chat_jid,
    max_messages=1000,
    resume=False  # Start fresh
)

if fetch_result["success"]:
    print(f"✅ Checkpoint created: {fetch_result['checkpoint']}")

    # Sync to Go database
    sync_result = sync_history_to_database()
    print(f"✅ Synced {sync_result['messages_synced']} messages")
else:
    print(f"❌ Failed: {fetch_result['message']}")
```

**When to use**:
- Syncing specific high-priority chats
- Avoiding full sync when only few chats need history
- Testing history sync on small scale

---

## Example 5: Resume Interrupted History Sync

```python
# Resume a history sync that was interrupted (power failure, timeout, etc.)
chat_jid = "1234567890@s.whatsapp.net"

# Check if checkpoint exists
status = get_sync_status(chat_jid=chat_jid)

if status.get("has_checkpoint"):
    print(f"Resuming from checkpoint: {status['checkpoint']}")
    print(f"Progress: {status['messages_synced']} messages already synced")

    # Resume sync
    result = resume_sync(
        chat_jid=chat_jid,
        max_messages=1000
    )

    if result["success"]:
        print(f"✅ Resumed sync: {result['messages_fetched']} new messages")

        # Sync to database
        sync_history_to_database()
    else:
        print(f"❌ Resume failed: {result['message']}")
else:
    print("No checkpoint found. Use fetch_history() to start fresh.")
```

**Checkpoint features**:
- Automatic checkpointing every 100 messages
- Resume from exact point after interruption
- Stored in Go database for persistence

---

## Example 6: Monitor Baileys Sync Progress

```python
import time

# Monitor long-running Baileys sync
def monitor_baileys_sync():
    """Monitor Baileys history sync progress in real-time."""

    print("Monitoring Baileys sync progress...")
    print("Press Ctrl+C to stop monitoring\n")

    try:
        while True:
            status = get_baileys_sync_status()

            if status.get("syncing"):
                progress = status.get("progress_percent", 0)
                messages = status.get("messages_synced", 0)

                # Progress bar
                bar_length = 40
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)

                print(f"\r{bar} {progress:.1f}% ({messages} messages)", end="")
            else:
                print("\n✅ Sync complete or idle")
                break

            time.sleep(2)  # Check every 2 seconds

    except KeyboardInterrupt:
        print("\n⚠️ Monitoring stopped")

# Usage
monitor_baileys_sync()
```

**Output**:
```
Monitoring Baileys sync progress...
Press Ctrl+C to stop monitoring

████████████████████████████████░░░░░░░░ 78.3% (6543 messages)
```

---

## Example 7: Mark Community as Read with History (Flagship Hybrid)

```python
# The flagship hybrid operation: combines ALL three layers
# Baileys retrieves → Sync orchestrates → Go marks as read

community_jid = "120363143634035041@g.us"

print("Starting flagship hybrid operation...")
print("This combines:")
print("  1. Baileys: Retrieve full community history")
print("  2. Sync: Transfer to Go database")
print("  3. Go: Mark all messages as read")
print()

result = mark_community_as_read_with_history(
    community_jid=community_jid,
    sync_timeout=600  # 10 minutes max
)

if result["success"]:
    # History sync details (Baileys)
    print("📥 Baileys History Sync:")
    print(f"  Messages synced: {result['history_sync_details']['messages_synced']}")
    print(f"  Duration: {result['history_sync_details']['sync_duration_seconds']}s")

    # Database sync details (Orchestrator)
    print("\n🔄 Database Sync:")
    print(f"  Messages transferred: {result.get('db_sync_details', {}).get('messages_synced', 'N/A')}")

    # Mark as read details (Go)
    print("\n✅ Mark as Read:")
    total_marked = sum(result["mark_as_read_details"].values())
    print(f"  Total marked: {total_marked} messages")
    print(f"  Across {len(result['mark_as_read_details'])} groups")

    # Per-group breakdown
    print("\n📊 Per-Group Results:")
    for group_jid, count in result["mark_as_read_details"].items():
        print(f"  - {group_jid}: {count} messages")
else:
    print(f"❌ Operation failed: {result['message']}")

    # Diagnose which step failed
    if "history_sync" in result.get("error_code", ""):
        print("⚠️ Failed at Baileys history sync step")
    elif "database_sync" in result.get("error_code", ""):
        print("⚠️ Failed at database sync step")
    else:
        print("⚠️ Failed at Go mark-as-read step")
```

**This is the MOST POWERFUL tool** - handles everything automatically:
- No manual sync required
- Handles deduplication
- Comprehensive error handling
- Cleanup of temp data

---

## Example 8: Search Historical Messages (Hybrid Workflow)

```python
# Multi-step workflow: Sync history → Query messages
def search_historical_messages(search_term, after_date=None):
    """Search messages with guaranteed history coverage."""

    print(f"🔍 Searching for: '{search_term}'")
    print("=" * 60)

    # Step 1: Ensure history is synced
    print("[1/3] Checking message statistics...")
    stats = get_message_statistics()

    if stats["total_messages"] == 0:
        print("⚠️ No messages in database. Running full history sync...")

        # Retrieve full history
        history_result = retrieve_full_history(
            wait_for_completion=True,
            timeout=1200
        )

        if not history_result["success"]:
            print(f"❌ History sync failed: {history_result['message']}")
            return

        # Sync to database
        sync_history_to_database()
        print("✅ History synced")
    else:
        print(f"✅ Database has {stats['total_messages']} messages")

    # Step 2: Query messages
    print(f"\n[2/3] Searching messages...")
    results = query_synced_messages(
        content=search_term,
        after_time=after_date,
        limit=50
    )

    # Step 3: Display results
    print(f"\n[3/3] Results: {results['total']} matches")

    if results["total"] == 0:
        print("No matches found")
        return

    # Group by chat
    by_chat = {}
    for msg in results["messages"]:
        chat_jid = msg["chat_jid"]
        if chat_jid not in by_chat:
            by_chat[chat_jid] = []
        by_chat[chat_jid].append(msg)

    # Display grouped results
    print(f"\nFound in {len(by_chat)} chats:")
    for chat_jid, messages in by_chat.items():
        print(f"\n📱 {chat_jid} ({len(messages)} matches):")

        for msg in messages[:3]:  # Show first 3
            sender = msg.get("sender_name", "Unknown")
            timestamp = msg["timestamp"]
            preview = msg["content"][:60] + "..." if len(msg["content"]) > 60 else msg["content"]
            print(f"  [{timestamp}] {sender}: {preview}")

# Usage
search_historical_messages("birthday", after_date="2025-01-01T00:00:00Z")
```

---

## Example 9: Business Catalog Browse (Baileys Exclusive)

```python
# Browse business catalog - ONLY available via Baileys bridge
business_jid = "1234567890@s.whatsapp.net"

print(f"Browsing catalog for {business_jid}...")

# Step 1: Get business profile (Go bridge)
profile = get_business_profile(jid=business_jid)

if not profile.get("is_business"):
    print("❌ This is not a business account")
    exit(1)

print(f"✅ Business: {profile.get('description', 'N/A')}")
print(f"Category: {profile.get('category', 'N/A')}")

# Step 2: Get catalog (Baileys bridge - exclusive)
catalog = get_business_catalog(jid=business_jid)

print(f"\n📦 Catalog: {catalog['product_count']} products")

# Step 3: Browse products
for product in catalog["products"][:10]:  # First 10
    print(f"\n{product['name']}")
    print(f"  Price: {product.get('price', 'N/A')}")
    print(f"  ID: {product['id']}")

    # Get detailed info (Baileys bridge)
    details = get_product_details(
        jid=business_jid,
        product_id=product["id"]
    )

    print(f"  Description: {details.get('description', 'N/A')[:100]}")
    print(f"  Availability: {details.get('availability', 'N/A')}")
```

**Why Baileys only**: whatsmeow doesn't implement WhatsApp Business catalog protocol.

---

## Example 10: Comprehensive System Health Check

```python
# Check health of entire hybrid system
def comprehensive_health_check():
    """Verify all components of hybrid architecture."""

    print("🏥 Hybrid System Health Check")
    print("=" * 60)

    # Check both bridges
    status = backend_status()

    print("\n[Backend Status]")
    print(f"Overall: {'✅ Healthy' if status['overall_status'] == 'healthy' else '❌ Unhealthy'}")
    print(f"Go Bridge (8080): {'✅' if status['go_bridge']['healthy'] else '❌'}")
    print(f"Baileys Bridge (8081): {'✅' if status['baileys_bridge']['healthy'] else '❌'}")

    # Check database
    print("\n[Database Status]")
    stats = get_message_statistics()
    print(f"Total messages: {stats['total_messages']}")
    print(f"Total chats: {stats['total_chats']}")
    print(f"Oldest message: {stats.get('oldest_message', 'N/A')}")
    print(f"Newest message: {stats.get('newest_message', 'N/A')}")

    # Check Baileys sync
    print("\n[Baileys Sync Status]")
    baileys = get_baileys_sync_status()

    if baileys.get("syncing"):
        print(f"⚠️ Sync in progress: {baileys.get('progress_percent', 0)}%")
        print(f"   Messages synced: {baileys.get('messages_synced', 0)}")
    else:
        print("✅ Sync idle")

    # Check checkpoints
    print("\n[Sync Checkpoints]")
    checkpoints = get_sync_checkpoints()

    if checkpoints.get("count", 0) > 0:
        print(f"Active checkpoints: {checkpoints['count']}")
        for cp in checkpoints.get("checkpoints", [])[:5]:
            print(f"  - {cp['chat_jid']}: {cp['messages_synced']} messages")
    else:
        print("No active checkpoints")

    print("\n" + "=" * 60)

    # Overall verdict
    if status['overall_status'] == 'healthy' and not baileys.get("syncing"):
        print("✅ System ready for operations")
        return True
    else:
        print("⚠️ System not ready - address issues above")
        return False

# Usage
if comprehensive_health_check():
    print("\nProceeding with operations...")
```

---

## Architecture Decision Guide

**When to use Go Bridge directly**:
- ✅ Sending/receiving messages
- ✅ Managing chats (archive, mute, pin)
- ✅ Contact operations
- ✅ Mark single chat as read
- ✅ Newsletter operations

**When to use Baileys Bridge directly**:
- ✅ Full history retrieval (`retrieve_full_history`)
- ✅ Business catalog browsing
- ✅ Advanced WhatsApp Web features

**When to use Hybrid Operations**:
- ✅ Mark community as read with history guarantee
- ✅ First-time message sync
- ✅ Historical message search
- ✅ Operations requiring both bridges

---

## Performance Comparison

| Operation | Go Only | Baileys Only | Hybrid | Recommended |
|-----------|---------|--------------|--------|-------------|
| Send message | 50ms | N/A | N/A | Go ✅ |
| Mark chat as read (DB) | 100ms | N/A | N/A | Go ✅ |
| Mark chat as read (full) | ❌ Broken | 2-5 min | 2-5 min | Hybrid ✅ |
| List chats | 80ms | N/A | N/A | Go ✅ |
| Retrieve history | ❌ Broken | 5-20 min | 5-20 min | Baileys/Hybrid ✅ |
| Business catalog | ❌ N/A | 1-2s | N/A | Baileys ✅ |
| Search messages | 200ms | N/A | 200ms* | Hybrid ✅ |

*After initial history sync

---

## Related Documentation

- [Basic Messaging Examples](./basic-messaging.md)
- [Community Management Examples](./community-management.md)
- [API Reference](../../API_REFERENCE.md)
- [Backend Routing Decision Tree](../BACKEND_ROUTING.md)
- [Troubleshooting Guide](../../TROUBLESHOOTING.md)
