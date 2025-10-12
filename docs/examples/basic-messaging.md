# Basic Messaging Examples

This guide demonstrates fundamental messaging workflows using the WhatsApp MCP.

---

## Example 1: Send Text Message to Contact

```python
# Step 1: Verify contact is on WhatsApp
check = check_is_on_whatsapp(phone="+1234567890")

if check["is_on_whatsapp"]:
    # Step 2: Send message
    result = send_text_message_v2(
        chat_jid=check["jid"],
        text="Hello! This is a test message from WhatsApp MCP."
    )

    if result["success"]:
        print(f"✅ Message sent successfully")
        print(f"Message ID: {result['message_id']}")
    else:
        print(f"❌ Failed: {result['message']}")
else:
    print(f"❌ {check['phone']} is not on WhatsApp")
```

**When to use**: Sending text messages to phone numbers.

**Note**: Always verify the contact is on WhatsApp first to avoid errors.

---

## Example 2: Send Image with Caption

```python
# Prepare image file on server
image_path = "/home/user/photos/vacation.jpg"

# Send image with caption
result = send_media_message_v2(
    chat_jid="1234567890@s.whatsapp.net",
    media_path=image_path,
    media_type="image",
    caption="Check out this beautiful sunset! 🌅"
)

if result["success"]:
    print(f"✅ Image sent: {result['message_id']}")
```

**Supported media types**:
- `image` - JPEG, PNG, GIF (max 16MB)
- `video` - MP4, MOV (max 64MB)
- `audio` - MP3, WAV, OGG
- `document` - PDF, DOCX, ZIP, etc.

---

## Example 3: React to a Message

```python
# React with emoji to a specific message
result = react_to_message_v2(
    chat_jid="1234567890@s.whatsapp.net",
    message_id="3EB0A12345ABCDEF",
    emoji="👍"
)

if result["success"]:
    print("✅ Reaction added")
```

**Popular emojis**: 👍 ❤️ 😂 😮 😢 🙏 🎉

**To remove reaction**: Send empty string as emoji

---

## Example 4: Edit Sent Message

```python
# Edit a message you previously sent (within 15 minutes)
result = edit_message_v2(
    message_id="3EB0A12345ABCDEF",
    new_text="Updated message content"
)

if result["success"]:
    print("✅ Message edited")
else:
    # Check if edit window expired
    if "EDIT_WINDOW_EXPIRED" in result.get("error_code", ""):
        print("❌ Can't edit - more than 15 minutes passed")
```

**WhatsApp edit rules**:
- Maximum 15 minutes after sending
- Text messages only (not media)
- Edit history visible to recipient

---

## Example 5: Delete Message

```python
# Delete (revoke) a message for everyone
result = delete_message_v2(message_id="3EB0A12345ABCDEF")

if result["success"]:
    print("✅ Message deleted")
```

**Delete window**: Varies by WhatsApp version, typically 1-2 days.

---

## Example 6: Forward Message

```python
# Forward message to another chat
result = forward_message_v2(
    message_id="3EB0A12345ABCDEF",
    to_chat_jid="9876543210@s.whatsapp.net"
)

if result["success"]:
    print(f"✅ Message forwarded: {result['message_id']}")
```

**Note**: Forwarded messages show "Forwarded" label in recipient's chat.

---

## Example 7: Send Voice Note

```python
# Send audio as voice note (shows with waveform in WhatsApp)
result = send_voice_note_v2(
    chat_jid="1234567890@s.whatsapp.net",
    audio_path="/home/user/recordings/voice.ogg"
)

if result["success"]:
    print("✅ Voice note sent")
```

**Format**: Use OGG Opus for best compatibility (MP3/WAV also supported).

---

## Example 8: Send Location

```python
# Send GPS coordinates
result = send_location_v2(
    chat_jid="1234567890@s.whatsapp.net",
    latitude=37.7749,
    longitude=-122.4194
)

if result["success"]:
    print("✅ Location sent")
```

**Coordinate ranges**:
- Latitude: -90 to 90
- Longitude: -180 to 180

---

## Example 9: Send Contact Card (vCard)

```python
# Prepare vCard format
vcard = """BEGIN:VCARD
VERSION:3.0
FN:John Doe
TEL;TYPE=CELL:+1234567890
EMAIL:john@example.com
END:VCARD"""

result = send_contact_v2(
    chat_jid="1234567890@s.whatsapp.net",
    vcard=vcard
)

if result["success"]:
    print("✅ Contact card sent")
```

**vCard format**: Standard vCard 3.0 specification.

---

## Example 10: Download Media from Message

```python
# Step 1: Find messages with media
messages = list_messages(
    chat_jid="1234567890@s.whatsapp.net",
    limit=20
)

# Step 2: Download media from a message
for msg in messages:
    if msg.get("media_type") == "image":
        result = download_media_v2(message_id=msg["message_id"])

        if result["success"]:
            print(f"✅ Downloaded to: {result['file_path']}")
            # File saved to server's filesystem
```

**Media storage**: Files saved to bridge's configured media directory.

---

## Error Handling Pattern

```python
def safe_send_message(chat_jid, text, max_retries=3):
    """Send message with automatic retry on rate limiting."""
    for attempt in range(max_retries):
        try:
            result = send_text_message_v2(chat_jid=chat_jid, text=text)

            if result["success"]:
                return result

            # Check for rate limiting
            if "RATE_LIMIT" in result.get("error_code", ""):
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"⏳ Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            # Non-recoverable error
            raise Exception(f"Send failed: {result['message']}")

        except Exception as e:
            if attempt == max_retries - 1:
                raise  # Final attempt failed
            print(f"Attempt {attempt + 1} failed: {e}")

    raise Exception(f"Failed after {max_retries} attempts")

# Usage
try:
    result = safe_send_message("1234567890@s.whatsapp.net", "Test message")
    print("✅ Message sent successfully")
except Exception as e:
    print(f"❌ Failed: {e}")
```

---

## Related Documentation

- [Community Management Examples](./community-management.md)
- [Hybrid Operations Examples](./hybrid-operations.md)
- [API Reference](../../API_REFERENCE.md)
- [Common Usage Patterns](../COMMON_PATTERNS.md)
