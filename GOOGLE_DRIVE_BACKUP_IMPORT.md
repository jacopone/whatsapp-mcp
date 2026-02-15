# Importing WhatsApp Backups from Google Drive

## Overview

WhatsApp automatically backs up your messages to Google Drive (on Android). These backups can be imported into your local database, but it requires several steps due to encryption.

## Option 1: Built-in History Sync (RECOMMENDED) ✅

**Use the `sync_all_history.py` script instead!** This is:
- ✅ Easier - just run one script
- ✅ Official - uses WhatsApp's native sync protocol
- ✅ Complete - gets ALL history from all devices
- ✅ Safe - no encryption key extraction needed

```bash
cd whatsapp-mcp
python sync_all_history.py
```

## Option 2: Google Drive Backup Import (ADVANCED)

Only use this if:
- You've lost access to your WhatsApp account
- You have an old backup you want to restore
- The built-in sync doesn't work for some reason

### What You Need

1. **Backup files from Google Drive**:
   - `msgstore.db.crypt14` (or crypt15) - Main encrypted database
   - `msgstore-YYYY-MM-DD.1.db.crypt14` - Older backups
   - Location: Google Drive > WhatsApp folder

2. **Encryption key** (64-character hex string):
   - Android 4.4+: `/data/data/com.whatsapp/files/key`
   - Rooted device OR extracted via ADB backup

3. **Decryption tool**:
   - WhatsApp Viewer (GUI)
   - wa-crypt-tools (Python)
   - Custom scripts

### Steps to Import Google Drive Backup

#### Step 1: Download Backup from Google Drive

```bash
# Install Google Drive CLI (rclone)
# Configure it to access your Google Drive
rclone copy "GoogleDrive:WhatsApp/" ~/whatsapp-backups/

# Or download manually:
# 1. Go to drive.google.com
# 2. Navigate to WhatsApp folder
# 3. Download msgstore.db.crypt14 (latest backup)
```

#### Step 2: Extract Encryption Key

**Option A: From Android Device (requires USB debugging)**

```bash
# Enable USB debugging on your phone first
# Settings > About Phone > tap Build Number 7 times
# Settings > Developer Options > USB Debugging

# Pull the key file
adb pull /data/data/com.whatsapp/files/key ~/whatsapp-backups/key

# Convert to hex (if needed)
xxd -p ~/whatsapp-backups/key | tr -d '\n' > ~/whatsapp-backups/key.hex
```

**Option B: From WhatsApp Database Backup (complex)**

Some third-party tools can extract the key from unencrypted backups or device backups.

#### Step 3: Decrypt the Backup

**Using Python script:**

```bash
# Install wa-crypt-tools
pip install pycryptodome

# Clone wa-crypt-tools
git clone https://github.com/ElDavoo/WhatsApp-Crypt14-Decrypter.git
cd WhatsApp-Crypt14-Decrypter

# Decrypt the backup
python3 decrypt14.py \
    ~/whatsapp-backups/key \
    ~/whatsapp-backups/msgstore.db.crypt14 \
    ~/whatsapp-backups/msgstore.db
```

#### Step 4: Import to Your Database

Create import script:

```python
#!/usr/bin/env python3
"""Import decrypted WhatsApp backup to Go database."""

import sqlite3
import requests
from datetime import datetime

def import_backup(backup_db_path, go_bridge_url="http://localhost:8080"):
    """Import messages from decrypted WhatsApp backup."""

    # Connect to decrypted backup
    backup_conn = sqlite3.connect(backup_db_path)
    backup_cursor = backup_conn.cursor()

    # Get all messages
    backup_cursor.execute("""
        SELECT
            m._id,
            m.key_remote_jid,
            m.key_from_me,
            m.timestamp,
            m.data,
            m.media_wa_type
        FROM message m
        WHERE m.key_remote_jid IS NOT NULL
        ORDER BY m.timestamp
    """)

    messages = backup_cursor.fetchall()
    print(f"Found {len(messages)} messages in backup")

    # Import to Go bridge via API
    imported = 0
    for msg_id, chat_jid, from_me, timestamp, content, media_type in messages:
        try:
            # Convert timestamp (WhatsApp uses milliseconds)
            dt = datetime.fromtimestamp(timestamp / 1000)

            # Send to Go bridge
            response = requests.post(
                f"{go_bridge_url}/api/messages/import",
                json={
                    "message_id": str(msg_id),
                    "chat_jid": chat_jid,
                    "is_from_me": bool(from_me),
                    "timestamp": dt.isoformat(),
                    "content": content or "",
                    "media_type": media_type
                }
            )

            if response.status_code == 200:
                imported += 1
                if imported % 100 == 0:
                    print(f"Imported {imported}/{len(messages)} messages...")

        except Exception as e:
            print(f"Error importing message {msg_id}: {e}")
            continue

    backup_conn.close()
    print(f"✓ Imported {imported} messages successfully!")

if __name__ == "__main__":
    import_backup("~/whatsapp-backups/msgstore.db")
```

### Challenges with Google Drive Import

1. **Encryption**: WhatsApp backups are encrypted, requiring the device key
2. **Key extraction**: Getting the key requires root access or ADB backup
3. **Format changes**: WhatsApp changes encryption (crypt12 → crypt14 → crypt15)
4. **Incomplete data**: Backups may not include:
   - Media files (need separate download)
   - Recent messages (only backs up daily)
   - Deleted messages
   - Some metadata

### Why Built-in Sync is Better

The `sync_all_history.py` script uses **WhatsApp's official sync protocol** via Baileys:

✅ **No encryption hassle** - Connects to WhatsApp servers directly
✅ **Complete history** - Gets ALL messages from all linked devices
✅ **Real-time** - Includes latest messages
✅ **All chats** - Individual, group, and community messages
✅ **Metadata** - Reactions, edits, read receipts, etc.
✅ **Safe** - Uses official API, no device rooting needed

## Recommendation

**Always use `sync_all_history.py` first.** Only attempt Google Drive import if:
- You've lost access to your WhatsApp account
- You have an old backup you specifically want to restore
- You're comfortable with encryption, ADB, and potential risks

## References

- [WhatsApp Encryption Whitepaper](https://www.whatsapp.com/security/WhatsApp-Security-Whitepaper.pdf)
- [wa-crypt-tools GitHub](https://github.com/ElDavoo/WhatsApp-Crypt14-Decrypter)
- [WhatsApp Database Structure](https://github.com/WHOISshuvam/WhatsApp-Database-Structure)
