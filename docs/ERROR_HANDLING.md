# Error Handling Reference

Comprehensive guide to handling errors across all 75 WhatsApp MCP tools.

---

## Common Error Codes

### Connection & Bridge Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `BRIDGE_UNREACHABLE` | Cannot connect to Go or Baileys bridge | Verify bridges are running at localhost:8080 (Go) and localhost:8081 (Baileys) |
| `BAILEYS_NOT_CONNECTED` | Baileys bridge not authenticated with WhatsApp | Scan QR code with WhatsApp app to authenticate Baileys |
| `CONNECTION_ERROR` | Network error communicating with bridge | Check network connectivity and bridge availability |
| `TIMEOUT` | Request exceeded timeout duration | Increase timeout parameter or check bridge responsiveness |
| `BACKEND_UNHEALTHY` | One or both backends not responding | Run `backend_status()` to diagnose specific bridge issues |

### WhatsApp API Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `WHATSAPP_API_ERROR` | WhatsApp service returned an error | Check WhatsApp connection status and retry |
| `RATE_LIMIT` | Too many requests to WhatsApp | Wait before retrying, implement exponential backoff |
| `AUTH_EXPIRED` | WhatsApp authentication session expired | Re-scan QR code to re-authenticate (~20 day sessions) |
| `DEVICE_LIMIT` | Maximum number of linked devices reached | Remove unused devices from WhatsApp settings |

### JID & Parameter Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `INVALID_JID` | Chat/contact JID is malformed | Verify JID format: phone@s.whatsapp.net (direct), group@g.us (group), newsletter@newsletter (newsletter) |
| `INVALID_PHONE_FORMAT` | Phone number format incorrect | Include country code with + prefix (e.g., "+1234567890") |
| `MISSING_IDENTIFIER` | Neither JID nor phone provided | Provide at least one identifier (jid or phone) |
| `INVALID_COORDINATES` | Latitude/longitude out of range | Latitude: -90 to 90, Longitude: -180 to 180 |

### Message & Content Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `MESSAGE_NOT_FOUND` | Message ID doesn't exist | Verify message ID is correct and message exists in chat |
| `NO_MEDIA_CONTENT` | Message doesn't contain media | Verify message has image, video, audio, or document attachment |
| `FILE_NOT_FOUND` | Media file doesn't exist at path | Verify file path is correct and accessible by bridge |
| `FILE_TOO_LARGE` | File exceeds WhatsApp size limits | Compress file (16MB images, 64MB videos typically) |
| `INVALID_MEDIA_TYPE` | Media type not supported | Use: "image", "video", "audio", or "document" |
| `TEXT_TOO_LONG` | Text exceeds maximum length | Shorten message (status messages: 139 chars max) |

### Chat & Contact Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `CHAT_NOT_FOUND` | Chat doesn't exist in database | Verify JID is correct and chat is accessible |
| `CONTACT_NOT_FOUND` | Contact doesn't exist | Verify contact is in WhatsApp contacts |
| `EMPTY_CHAT` | Chat exists but has no messages | Informational only - not an error |
| `NO_RESULTS` | Search returned no matches | Broaden search query or verify data exists |

### History Sync Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `HISTORY_SYNC_TIMEOUT` | History sync exceeded timeout | Increase `sync_timeout` parameter for large histories |
| `HISTORY_SYNC_FAILED` | Baileys encountered error during sync | Check Baileys bridge logs and connectivity |
| `DATABASE_SYNC_FAILED` | Failed to sync Baileys → Go database | Check Go bridge database health |
| `SYNC_IN_PROGRESS` | Another sync already running | Wait for completion or use `cancel_sync()` |
| `NO_CHECKPOINT` | No checkpoint exists for resume | Use `fetch_history()` to start fresh sync |

### Business & Newsletter Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `NOT_BUSINESS_ACCOUNT` | JID is not a WhatsApp Business account | Verify account type - only Business accounts have catalogs |
| `NO_CATALOG_FOUND` | Business account has no catalog | Business hasn't set up product catalog |
| `PRODUCT_NOT_FOUND` | Product ID doesn't exist | Verify product ID from `get_business_catalog()` |
| `NEWSLETTER_NOT_FOUND` | Newsletter doesn't exist | Verify newsletter JID and access |
| `ALREADY_SUBSCRIBED` | Already subscribed to newsletter | No action needed - subscription active |
| `NOT_SUBSCRIBED` | Not subscribed to newsletter | Subscribe before accessing newsletter content |

### Privacy & Permissions Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `PRIVACY_RESTRICTED` | Contact has restricted visibility | Respect user's privacy settings |
| `ACCESS_DENIED` | Not authorized to access resource | Subscribe or join group before accessing |
| `MAX_PINS_REACHED` | Maximum pinned chats limit (3) | Unpin another chat before pinning new one |
| `NOT_GROUP_MEMBER` | Not a member of the group | Join group before performing operation |

---

## Error Handling Patterns

### Pattern 1: Retry with Exponential Backoff

```python
import time

def send_with_retry(chat_jid, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = send_text_message_v2(chat_jid=chat_jid, text=text)
            return result
        except Exception as e:
            if "RATE_LIMIT" in str(e):
                # Exponential backoff
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise  # Re-raise non-rate-limit errors

    raise Exception(f"Failed after {max_retries} retries")
```

### Pattern 2: Graceful Degradation

```python
def get_contact_info(jid):
    try:
        # Try to get full details
        details = get_contact_details_v2(jid=jid)
        return details["contact"]
    except Exception as e:
        if "CONTACT_NOT_FOUND" in str(e):
            # Fallback to basic search
            contacts = search_contacts_v2(query=jid.split("@")[0])
            if contacts["count"] > 0:
                return contacts["contacts"][0]

        # Ultimate fallback
        return {"jid": jid, "name": "Unknown", "phone": jid.split("@")[0]}
```

### Pattern 3: Health Check Before Operation

```python
def safe_bulk_operation(operation_func, items):
    # Check system health first
    health = backend_status()

    if health["overall_status"] != "healthy":
        raise Exception("System unhealthy - aborting bulk operation")

    results = []
    failures = []

    for item in items:
        try:
            result = operation_func(item)
            results.append(result)
        except Exception as e:
            failures.append({"item": item, "error": str(e)})
            # Continue processing other items

    return {
        "successes": results,
        "failures": failures,
        "success_rate": len(results) / len(items)
    }
```

### Pattern 4: Timeout Handling for Long Operations

```python
from concurrent.futures import TimeoutError
import signal

def history_sync_with_timeout(timeout_seconds=600):
    def timeout_handler(signum, frame):
        raise TimeoutError("History sync exceeded timeout")

    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        result = retrieve_full_history(
            wait_for_completion=True,
            timeout=timeout_seconds
        )
        signal.alarm(0)  # Cancel timeout
        return result
    except TimeoutError:
        print("⏱️ Sync timed out. Checking progress...")
        status = get_baileys_sync_status()
        print(f"Progress: {status['progress_percent']}%")
        raise
```

### Pattern 5: Validation Before API Call

```python
def validate_and_send(chat_jid, text):
    # Validate JID format
    if not chat_jid or "@" not in chat_jid:
        raise ValueError("INVALID_JID: JID must include @ symbol")

    # Validate text length
    if len(text) > 4000:
        raise ValueError("TEXT_TOO_LONG: Message exceeds 4000 characters")

    # Validate JID domain
    valid_domains = ["s.whatsapp.net", "g.us", "newsletter"]
    domain = chat_jid.split("@")[1]
    if not any(d in domain for d in valid_domains):
        raise ValueError(f"INVALID_JID: Domain '{domain}' not recognized")

    # All validations passed
    return send_text_message_v2(chat_jid=chat_jid, text=text)
```

---

## Debugging Tips

### 1. Enable Verbose Logging

```python
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now errors will include full stack traces
```

### 2. Check Backend Health First

```python
# Always check before bulk operations
def preflight_check():
    status = backend_status()

    print("=== Preflight Check ===")
    print(f"Overall: {status['overall_status']}")
    print(f"Go Bridge: {'✅' if status['go_bridge']['healthy'] else '❌'}")
    print(f"Baileys Bridge: {'✅' if status['baileys_bridge']['healthy'] else '❌'}")

    if status["baileys_bridge"]["syncing"]:
        print(f"⚠️ Baileys syncing ({status['baileys_bridge']['progress_percent']}%)")

    return status["overall_status"] == "healthy"
```

### 3. Capture Error Context

```python
def execute_with_context(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_context = {
            "function": func.__name__,
            "args": args,
            "kwargs": kwargs,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(f"Error context: {error_context}")
        raise  # Re-raise with context printed
```

### 4. Test Connectivity

```bash
# Test Go bridge
curl http://localhost:8080/health

# Test Baileys bridge
curl http://localhost:8081/health

# Check processes
ps aux | grep -E "main.go|baileys-bridge"
```

---

## Error Response Structure

All tools return errors in a consistent structure:

```json
{
  "success": false,
  "message": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "details": {
    "field": "Additional context"
  }
}
```

**Always check `success` field first**, then inspect `error_code` for programmatic handling.

---

## Getting Help

If errors persist after following resolution steps:

1. Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) (coming soon)
2. Review bridge logs:
   - Go: Check terminal output where `go run main.go` is running
   - Baileys: Check terminal output where `npm run dev` is running
3. Report issue on [GitHub](https://github.com/lharries/whatsapp-mcp/issues) with:
   - Error code and full message
   - Tool name and parameters used
   - Bridge status output (`backend_status()`)
   - Steps to reproduce
