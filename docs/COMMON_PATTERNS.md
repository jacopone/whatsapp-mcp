# Common Usage Patterns

This guide demonstrates common WhatsApp MCP workflows combining multiple tools.

---

## Pattern 1: Send Message with Delivery Confirmation

```python
# Check contact is on WhatsApp
check = check_is_on_whatsapp(phone="+1234567890")

if check["is_on_whatsapp"]:
    # Send message
    result = send_text_message_v2(
        chat_jid=check["jid"],
        text="Hello from WhatsApp MCP!"
    )

    # Verify delivery
    if result["success"]:
        print(f"✅ Message sent to {check['jid']}")
```

---

## Pattern 2: Mark All Community Messages as Read (with History)

```python
# RECOMMENDED: Use hybrid tool for complete coverage
community_jid = "120363143634035041@g.us"

result = mark_community_as_read_with_history(
    community_jid=community_jid,
    sync_timeout=600  # 10 minutes for large histories
)

print(f"Marked {result['mark_as_read_details'].values().sum()} messages across all groups")
```

---

## Pattern 3: Search Message History

```python
# Step 1: Retrieve full history (first time only)
sync_result = retrieve_full_history(wait_for_completion=True, timeout=600)

# Step 2: Sync to Go database
sync_history_to_database()

# Step 3: Query messages
messages = query_synced_messages(
    content="birthday",
    after_time="2025-01-01T00:00:00Z",
    limit=50
)

for msg in messages["messages"]:
    print(f"{msg['timestamp']}: {msg['content']}")
```

---

## Pattern 4: Bulk Chat Management

```python
# Get all chats
chats = list_chats_v2(limit=100)

# Archive old chats
for chat in chats["chats"]:
    if chat["last_message_time"] < "2025-01-01":
        archive_chat(chat["jid"])

# Mark all active chats as read
for chat in chats["chats"]:
    if chat["unread_count"] > 0 and not chat["archived"]:
        mark_chat_read_v2(chat["jid"])
```

---

## Pattern 5: Contact Discovery and Profile

```python
# Search for contact
contacts = search_contacts_v2(query="John")

if contacts["count"] > 0:
    jid = contacts["contacts"][0]["jid"]

    # Get full details
    details = get_contact_details_v2(jid=jid)

    # Get profile picture
    picture = get_profile_picture_v2(jid=jid)

    # Get status message
    status = get_contact_status_v2(jid=jid)

    print(f"Name: {details['contact']['name']}")
    print(f"Phone: {details['contact']['phone']}")
    print(f"Status: {status['status']}")
```

---

## Pattern 6: Download All Media from Chat

```python
# List messages with media
messages = list_messages(
    chat_jid="1234567890@s.whatsapp.net",
    limit=100
)

for msg in messages:
    if msg.get("media_type"):
        # Download media
        result = download_media_v2(message_id=msg["message_id"])
        print(f"Downloaded: {result['file_path']}")
```

---

## Pattern 7: Privacy Configuration

```python
# Set all privacy settings to contacts-only
update_last_seen_privacy(value="contacts")
update_profile_picture_privacy(value="contacts")
update_status_privacy(value="contacts")
update_online_privacy(value="match_last_seen")

# Verify settings
settings = get_privacy_settings()
print(f"Privacy configured: {settings['settings']}")
```

---

## Pattern 8: Newsletter Management

```python
# Subscribe to newsletter
subscribe_to_newsletter(jid="120363271234567890@newsletter")

# Get info
info = get_newsletter_info(jid="120363271234567890@newsletter")
print(f"Subscribed to: {info['name']} ({info['subscriber_count']} subscribers)")

# React to latest post
react_to_newsletter_post(
    jid="120363271234567890@newsletter",
    message_id="3EB0ABC123",
    emoji="👍"
)
```

---

## Pattern 9: System Health Check Before Operations

```python
# Always check health before bulk operations
health = backend_status()

if health["overall_status"] != "healthy":
    print("⚠️ System not healthy. Aborting operation.")

    # Check specific bridges
    if not health["go_bridge"]["healthy"]:
        print("❌ Go bridge offline")
    if not health["baileys_bridge"]["healthy"]:
        print("❌ Baileys bridge offline")
    exit(1)

# Proceed with operation
print("✅ System healthy. Proceeding...")
```

---

## Pattern 10: Business Catalog Browse

```python
# Get business profile
profile = get_business_profile(jid="1234567890@s.whatsapp.net")
print(f"Business: {profile['description']}")

# Browse catalog (requires Baileys)
catalog = get_business_catalog(jid="1234567890@s.whatsapp.net")
print(f"Found {catalog['product_count']} products")

# Get product details
for product in catalog["products"][:5]:
    details = get_product_details(
        jid="1234567890@s.whatsapp.net",
        product_id=product["id"]
    )
    print(f"{details['name']}: {details['price']}")
```
