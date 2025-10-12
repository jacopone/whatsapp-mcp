# Community Management Examples

This guide demonstrates workflows for managing WhatsApp Communities (umbrella groups with multiple subgroups).

---

## Understanding WhatsApp Communities

**Community Structure**:
```
Community (e.g., "School Parent Association")
├── Announcements Group
├── Grade 1 Parents Group
├── Grade 2 Parents Group
└── PTA Committee Group
```

**JID Format**: Communities use `@g.us` domain like groups.

---

## Example 1: List All Communities

```python
# Get all communities you're part of
result = list_communities(limit=50)

print(f"Found {result['count']} communities:")
for community in result["communities"]:
    print(f"- {community['name']} ({community['jid']})")
    print(f"  Groups: {community.get('group_count', 'N/A')}")
```

**Output**:
```
Found 2 communities:
- School Parent Association (120363143634035041@g.us)
  Groups: 4
- Neighborhood Watch (120363298765432109@g.us)
  Groups: 3
```

---

## Example 2: Get All Groups in a Community

```python
# Retrieve all subgroups within a community
community_jid = "120363143634035041@g.us"

result = get_community_groups(community_jid=community_jid, limit=100)

print(f"Community: {result['community_name']}")
print(f"Groups ({result['group_count']}):")

for group in result["groups"]:
    print(f"- {group['name']}")
    print(f"  JID: {group['jid']}")
    print(f"  Unread: {group.get('unread_count', 0)}")
```

**Output**:
```
Community: School Parent Association
Groups (4):
- Announcements
  JID: 120363111111111111@g.us
  Unread: 0
- Grade 1 Parents
  JID: 120363222222222222@g.us
  Unread: 15
- Grade 2 Parents
  JID: 120363333333333333@g.us
  Unread: 8
- PTA Committee
  JID: 120363444444444444@g.us
  Unread: 3
```

---

## Example 3: Mark All Community Messages as Read (Database Only)

```python
# Mark all messages in all community groups as read
# NOTE: Only marks messages already in database
community_jid = "120363143634035041@g.us"

result = mark_community_as_read(community_jid=community_jid)

if result["success"]:
    total_marked = sum(result["details"].values())
    print(f"✅ Marked {total_marked} messages as read")

    # Show per-group breakdown
    for group_jid, count in result["details"].items():
        print(f"  - {group_jid}: {count} messages")
else:
    print(f"❌ Failed: {result['message']}")
```

**Limitation**: Only marks messages that were previously synced to database. For complete coverage, use Example 4.

---

## Example 4: Mark All Community Messages as Read (with History Sync)

```python
# RECOMMENDED: Hybrid operation that retrieves full history first
# This ensures ALL messages are marked, not just what's in database

community_jid = "120363143634035041@g.us"

print("Starting comprehensive mark-as-read operation...")
print("This may take 2-10 minutes depending on history size.")

result = mark_community_as_read_with_history(
    community_jid=community_jid,
    sync_timeout=600  # 10 minutes max
)

if result["success"]:
    # Show history sync results
    print("\n📥 History Sync:")
    print(f"  Messages synced: {result['history_sync_details']['messages_synced']}")
    print(f"  Duration: {result['history_sync_details']['sync_duration_seconds']}s")

    # Show mark-as-read results
    total_marked = sum(result["mark_as_read_details"].values())
    print(f"\n✅ Marked {total_marked} messages as read across all groups")
else:
    print(f"❌ Failed: {result['message']}")
```

**When to use**:
- First time marking a community as read
- When you haven't used WhatsApp for days/weeks
- To ensure 100% message coverage

**Performance**:
- Small communities (<1000 messages): 1-2 minutes
- Large communities (>5000 messages): 5-10 minutes

---

## Example 5: Monitor Unread Messages in Community

```python
# Create dashboard showing unread counts per group
community_jid = "120363143634035041@g.us"

# Get all groups
groups_result = get_community_groups(community_jid=community_jid)

# Get unread count for each group
print(f"📊 Unread Messages Dashboard - {groups_result['community_name']}")
print("=" * 60)

total_unread = 0
for group in groups_result["groups"]:
    # Get chat metadata for unread count
    chat = get_chat_metadata_v2(chat_jid=group["jid"])
    unread = chat["chat"].get("unread_count", 0)

    total_unread += unread

    status = "🔴" if unread > 10 else "🟡" if unread > 0 else "🟢"
    print(f"{status} {group['name']:<30} {unread:>4} unread")

print("=" * 60)
print(f"Total: {total_unread} unread messages")
```

**Output**:
```
📊 Unread Messages Dashboard - School Parent Association
============================================================
🟢 Announcements                     0 unread
🔴 Grade 1 Parents                  15 unread
🟡 Grade 2 Parents                   8 unread
🟡 PTA Committee                     3 unread
============================================================
Total: 26 unread messages
```

---

## Example 6: Bulk Mark Individual Groups as Read

```python
# Mark each group as read individually (without full history sync)
community_jid = "120363143634035041@g.us"

# Get all groups
groups_result = get_community_groups(community_jid=community_jid)

print(f"Marking {groups_result['group_count']} groups as read...")

for group in groups_result["groups"]:
    result = mark_chat_read_v2(chat_jid=group["jid"])

    if result["success"]:
        print(f"✅ {group['name']}: {result.get('count', 0)} messages marked")
    else:
        print(f"❌ {group['name']}: {result['message']}")
```

**Performance**: Fast (1-2 seconds per group) but only marks database messages.

---

## Example 7: Search Messages Across Community

```python
# Search for specific content across all community groups
community_jid = "120363143634035041@g.us"
search_term = "homework"

# First, ensure messages are synced
print("Syncing community messages...")
sync_result = mark_community_as_read_with_history(
    community_jid=community_jid,
    sync_timeout=300
)

# Get all groups
groups = get_community_groups(community_jid=community_jid)

# Search each group
print(f"\n🔍 Searching for '{search_term}' across {groups['group_count']} groups:")

total_matches = 0
for group in groups["groups"]:
    messages = query_synced_messages(
        chat_jid=group["jid"],
        content=search_term,
        limit=10
    )

    match_count = messages.get("total", 0)
    if match_count > 0:
        total_matches += match_count
        print(f"\n{group['name']}: {match_count} matches")

        # Show first 3 results
        for msg in messages["messages"][:3]:
            sender = msg.get("sender_name", "Unknown")
            preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            print(f"  - {sender}: {preview}")

print(f"\nTotal matches: {total_matches}")
```

---

## Example 8: Archive All Community Groups

```python
# Archive all groups in a community to reduce notification noise
community_jid = "120363143634035041@g.us"

groups_result = get_community_groups(community_jid=community_jid)

print(f"Archiving {groups_result['group_count']} groups...")

for group in groups_result["groups"]:
    result = archive_chat(chat_jid=group["jid"])

    if result["success"]:
        print(f"✅ Archived: {group['name']}")
    else:
        print(f"❌ Failed: {group['name']} - {result['message']}")
```

**To unarchive**: Use `unarchive_chat(chat_jid=group["jid"])` for each group.

---

## Example 9: Mute All Community Groups

```python
# Mute notifications for all groups (e.g., during work hours)
community_jid = "120363143634035041@g.us"

# Get all groups
groups_result = get_community_groups(community_jid=community_jid)

# Mute for 8 hours (28800 seconds)
mute_duration = 8 * 60 * 60

for group in groups_result["groups"]:
    result = mute_chat(
        chat_jid=group["jid"],
        duration_seconds=mute_duration
    )

    if result["success"]:
        print(f"🔇 Muted: {group['name']} for 8 hours")
```

**Durations**:
- `0` = Mute forever
- `28800` = 8 hours
- `86400` = 1 day
- `604800` = 1 week

---

## Example 10: Community Health Check

```python
# Comprehensive health check for community functionality
def community_health_check(community_jid):
    print("🏥 Community Health Check")
    print("=" * 60)

    # Check backend status
    backend = backend_status()
    if backend["overall_status"] != "healthy":
        print("❌ Backends unhealthy - aborting")
        return
    print("✅ Backends healthy")

    # Get community groups
    try:
        groups = get_community_groups(community_jid=community_jid)
        print(f"✅ Community accessible: {groups['group_count']} groups")
    except Exception as e:
        print(f"❌ Cannot access community: {e}")
        return

    # Check message sync status
    stats = get_message_statistics()
    print(f"✅ Database: {stats['total_messages']} messages synced")

    # Check Baileys sync status
    baileys = get_baileys_sync_status()
    if baileys.get("syncing"):
        print(f"⚠️ Baileys sync in progress: {baileys.get('progress_percent', 0)}%")
    else:
        print("✅ Baileys sync idle")

    print("=" * 60)
    print("Health check complete")

# Usage
community_health_check("120363143634035041@g.us")
```

---

## Performance Optimization Tips

**1. Use Database-Only Operations When Possible**
```python
# Fast but incomplete (only database messages)
mark_community_as_read(community_jid)

# Slow but complete (retrieves full history)
mark_community_as_read_with_history(community_jid)
```

**2. Limit History Sync Scope**
```python
# Don't sync more than you need
result = mark_community_as_read_with_history(
    community_jid=community_jid,
    sync_timeout=300  # Shorter timeout for faster completion
)
```

**3. Check Backend Health Before Bulk Operations**
```python
health = backend_status()
if health["overall_status"] != "healthy":
    print("⚠️ System not ready for bulk operation")
    exit(1)
```

---

## Related Documentation

- [Basic Messaging Examples](./basic-messaging.md)
- [Hybrid Operations Examples](./hybrid-operations.md)
- [API Reference - Communities](../../API_REFERENCE.md#6-communities)
- [Backend Routing](../BACKEND_ROUTING.md)
