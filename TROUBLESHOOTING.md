# WhatsApp MCP - Troubleshooting Guide

**Version**: 1.0
**Last Updated**: 2025-10-12

> Comprehensive troubleshooting guide for the WhatsApp MCP hybrid architecture (Go + Baileys + Python).

---

## Introduction

This guide helps you diagnose and resolve common issues with the WhatsApp MCP hybrid system. Each issue follows a structured format:

- **Symptoms**: What you observe when the issue occurs
- **Diagnosis**: Root cause analysis
- **Solution**: Step-by-step resolution
- **Verification**: How to confirm the fix worked

**Before You Start**:
- Ensure you've completed the [installation guide](./README.md#full-installation-guide)
- Have terminal access to check bridge processes
- Know how to access bridge logs (terminal output)

**Quick Diagnostics**:
```bash
# Check both bridges are running
curl http://localhost:8080/health  # Go bridge
curl http://localhost:8081/health  # Baileys bridge

# Check processes
ps aux | grep -E "main.go|baileys-bridge"

# Check ports
lsof -i :8080
lsof -i :8081
```

---

## Issue Index

### 🔴 Critical Severity
- [Prerequisites Missing](#1-prerequisites-missing) - Required software not installed
- [Go Bridge Port Conflict (8080)](#2-go-bridge-port-conflict-8080) - Port already in use
- [Baileys Bridge Port Conflict (8081)](#3-baileys-bridge-port-conflict-8081) - Port already in use
- [CGO Not Enabled on Windows](#4-cgo-not-enabled-on-windows) - Go SQLite compilation fails

### 🟠 High Severity
- [QR Code Not Displaying](#6-qr-code-not-displaying) - Can't authenticate
- [Authentication Expired After 20 Days](#7-authentication-expired-after-20-days) - Session timeout
- [WhatsApp Device Limit Reached](#8-whatsapp-device-limit-reached) - Too many linked devices
- [Both Bridges Running But MCP Shows Offline](#11-both-bridges-running-but-mcp-shows-offline) - Connectivity issue

### 🟡 Medium Severity
- [Messages in Baileys But Not in Go Database](#13-messages-in-baileys-but-not-in-go-database) - Sync failure
- [Sync Stalls at High Message Count](#14-sync-stalls-at-high-message-count) - Performance issue
- [Database Corruption](#16-database-corruption) - Data integrity problem

### 🟢 Low Severity
- [Slow Message Queries](#22-slow-message-queries) - Performance degradation
- [High Memory Usage](#23-high-memory-usage) - Resource consumption
- [Claude Desktop Timeout Errors](#24-claude-desktop-timeout-errors) - Operation timeouts

---

## Setup & Installation Issues

### 1. Prerequisites Missing

**Symptoms**:
- `command not found: go` when running Go bridge
- `command not found: node` or `command not found: npm` when running Baileys bridge
- `command not found: uv` when configuring MCP server
- Bridge fails to start with missing dependency errors

**Diagnosis**:
Required software (Go, Node.js, Python, UV) is not installed or not in PATH.

**Solution**:

**Install Go 1.24+**:
```bash
# macOS (via Homebrew)
brew install go

# Linux (Ubuntu/Debian)
wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin

# Windows
# Download installer from https://golang.org/dl/
```

**Install Node.js 20+**:
```bash
# macOS
brew install node

# Linux (Ubuntu/Debian) - via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
# Download installer from https://nodejs.org/
```

**Install Python 3.12+**:
```bash
# macOS
brew install python@3.12

# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3.12

# Windows
# Download installer from https://www.python.org/downloads/
```

**Install UV**:
```bash
# All platforms
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verification**:
```bash
go version  # Should show 1.24+
node --version  # Should show v20+
python3 --version  # Should show 3.12+
uv --version  # Should show installed version
```

---

### 2. Go Bridge Port Conflict (8080)

**Symptoms**:
- Go bridge fails to start with error: `listen tcp :8080: bind: address already in use`
- `curl http://localhost:8080/health` connects to wrong service

**Diagnosis**:
Another process is already using port 8080.

**Solution**:

**Find the conflicting process**:
```bash
# macOS/Linux
lsof -i :8080

# Windows
netstat -ano | findstr :8080
```

**Option A: Stop the conflicting process**:
```bash
# Kill the process using port 8080
kill -9 <PID>

# Or on Windows
taskkill /PID <PID> /F
```

**Option B: Change Go bridge port** (if port 8080 must remain occupied):
1. Edit `whatsapp-mcp/whatsapp-bridge/main.go`
2. Find the line: `router.Run(":8080")`
3. Change to: `router.Run(":8082")` (or another free port)
4. Update `unified-mcp/backends/go_client.py` to match new port

**Verification**:
```bash
curl http://localhost:8080/health
# Should return: {"status":"healthy"}
```

---

### 3. Baileys Bridge Port Conflict (8081)

**Symptoms**:
- Baileys bridge fails to start with error: `EADDRINUSE: address already in use :::8081`
- `curl http://localhost:8081/health` connects to wrong service

**Diagnosis**:
Another process is already using port 8081.

**Solution**:

**Find the conflicting process**:
```bash
# macOS/Linux
lsof -i :8081

# Windows
netstat -ano | findstr :8081
```

**Kill the process**:
```bash
# macOS/Linux
kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

**If you need to change the port**:
1. Edit `whatsapp-mcp/baileys-bridge/src/main.ts`
2. Find: `const PORT = 8081`
3. Change to desired port
4. Update `unified-mcp/backends/baileys_client.py` to match

**Verification**:
```bash
curl http://localhost:8081/health
# Should return health status
```

---

### 4. CGO Not Enabled on Windows

**Symptoms**:
- Go bridge compilation fails with: `Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work`
- Error during `go run main.go` or `go build`

**Diagnosis**:
CGO is disabled by default on Windows, but go-sqlite3 requires CGO for SQLite database operations.

**Solution**:

**1. Install C Compiler (MSYS2)**:
```bash
# Download MSYS2 from https://www.msys2.org/
# After installation, open MSYS2 terminal and run:
pacman -S mingw-w64-ucrt-x86_64-gcc
```

**2. Add to PATH**:
Add `C:\msys64\ucrt64\bin` to your Windows PATH environment variable.

**3. Enable CGO**:
```bash
# In PowerShell or CMD
cd whatsapp-mcp\whatsapp-bridge
go env -w CGO_ENABLED=1
```

**4. Build/Run**:
```bash
go run main.go
```

**Verification**:
```bash
go env CGO_ENABLED
# Should output: 1

# Bridge should start without CGO errors
```

**Alternative**: Use WSL2 (Windows Subsystem for Linux) which has native CGO support.

---

### 5. UV Not Found

**Symptoms**:
- MCP server fails to start with: `uv: command not found`
- Claude Desktop shows MCP server offline

**Diagnosis**:
UV package manager is not installed or not in PATH.

**Solution**:

**Install UV**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Add to PATH** (if not automatic):
```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.config/fish/config.fish
export PATH="$HOME/.cargo/bin:$PATH"

# Reload shell
source ~/.bashrc  # or restart terminal
```

**Verification**:
```bash
which uv
# Should show: /Users/you/.cargo/bin/uv or similar

uv --version
```

---

## Authentication Issues

### 6. QR Code Not Displaying

**Symptoms**:
- Terminal shows no QR code after starting bridge
- Bridge starts but authentication doesn't proceed
- Blank space where QR code should appear

**Diagnosis**:
Terminal doesn't support QR code rendering, or already authenticated.

**Solution**:

**Check if already authenticated**:
```bash
# Look for "Already logged in" or "Session loaded" message in terminal
# If present, authentication is complete - no QR needed
```

**Try different terminal**:
- macOS: Try iTerm2 or built-in Terminal.app
- Linux: Try GNOME Terminal, Konsole, or Kitty
- Windows: Try Windows Terminal (not CMD or PowerShell ISE)

**Clear session and retry**:
```bash
# Stop the bridge
# Delete session files
cd whatsapp-bridge
rm -rf store/whatsapp.db

# Or for Baileys
cd baileys-bridge
rm -rf auth_info_baileys/

# Restart bridge - fresh QR should appear
```

**Verification**:
QR code should appear as ASCII art in terminal. Scan with WhatsApp → Settings → Linked Devices → Link a Device.

---

### 7. Authentication Expired After 20 Days

**Symptoms**:
- Bridge was working, now shows "Session expired" or connection errors
- Cannot send messages, all tools return authentication errors
- Approximately 20 days since last QR code scan

**Diagnosis**:
WhatsApp sessions expire after ~20 days of inactivity and require re-authentication.

**Solution**:

**1. Stop both bridges**:
```bash
# Press Ctrl+C in both terminal windows
# Or kill processes
pkill -f "main.go"
pkill -f "baileys-bridge"
```

**2. Delete session data**:
```bash
# Go bridge
cd whatsapp-mcp/whatsapp-bridge
rm -rf store/whatsapp.db

# Baileys bridge
cd whatsapp-mcp/baileys-bridge
rm -rf auth_info_baileys/
```

**3. Restart bridges and re-scan QR codes**:
```bash
# Terminal 1: Go bridge
cd whatsapp-bridge
go run main.go
# Scan QR code #1

# Terminal 2: Baileys bridge
cd baileys-bridge
npm run dev
# Scan QR code #2
```

**Verification**:
```bash
# Both should return healthy status
curl http://localhost:8080/health
curl http://localhost:8081/health
```

---

### 8. WhatsApp Device Limit Reached

**Symptoms**:
- QR code scans successfully but connection fails
- WhatsApp shows "Too many devices linked" error
- Cannot link new device

**Diagnosis**:
WhatsApp limits linked devices to 5 (including the primary phone).

**Solution**:

**1. Check current linked devices**:
- Open WhatsApp on phone
- Go to Settings → Linked Devices
- View list of all linked devices

**2. Remove unused devices**:
- Tap on device you want to unlink
- Tap "Log Out"
- Confirm removal

**3. Retry QR code scan**:
- Restart the bridge that failed
- Scan new QR code

**Verification**:
Bridge should connect successfully and show "Connected" status.

---

### 9. Multiple WhatsApp Accounts on Bridges

**Symptoms**:
- Different phone numbers on Go bridge vs Baileys bridge
- Inconsistent message data between bridges
- Some operations work, others fail

**Diagnosis**:
Go and Baileys bridges authenticated with different WhatsApp accounts.

**Solution**:

**IMPORTANT**: Both bridges MUST authenticate with the SAME WhatsApp account.

**1. Stop both bridges**

**2. Clear ALL session data**:
```bash
# Go
rm -rf whatsapp-bridge/store/whatsapp.db

# Baileys
rm -rf baileys-bridge/auth_info_baileys/
```

**3. Authenticate Go bridge first**:
```bash
cd whatsapp-bridge
go run main.go
# Scan with WhatsApp account A
```

**4. Authenticate Baileys bridge with SAME account**:
```bash
cd baileys-bridge
npm run dev
# Scan with the SAME WhatsApp account A (not account B!)
```

**Verification**:
```bash
# Both should show same phone number in connection logs
# Check WhatsApp → Linked Devices - should show 2 devices for same account
```

---

### 10. QR Code Scan Successful But Bridge Disconnects

**Symptoms**:
- QR code scans successfully
- Bridge shows "Connected" briefly
- Then disconnects with error

**Diagnosis**:
Network connectivity issue or WhatsApp servers rejecting connection.

**Solution**:

**1. Check network connectivity**:
```bash
ping google.com
ping web.whatsapp.com
```

**2. Disable VPN/Proxy temporarily**:
- WhatsApp may block connections through VPNs
- Try direct internet connection

**3. Check firewall**:
```bash
# Ensure outbound HTTPS (443) is allowed
# WhatsApp uses websocket over HTTPS
```

**4. Wait and retry**:
- WhatsApp may temporarily rate-limit connection attempts
- Wait 5-10 minutes before retrying

**5. Check system time**:
```bash
# Ensure system time is accurate
date
# If wrong, sync with NTP
```

**Verification**:
Bridge maintains connection and doesn't disconnect after initial authentication.

---

## Bridge Connectivity Issues

### 11. Both Bridges Running But MCP Shows Offline

**Symptoms**:
- `ps aux` shows both bridge processes running
- `curl` to bridges fails or times out
- Claude Desktop shows WhatsApp MCP offline
- Tools return `BRIDGE_UNREACHABLE` error

**Diagnosis**:
Bridges are running but not listening on expected ports, or firewall blocking connections.

**Solution**:

**1. Verify bridges are listening**:
```bash
lsof -i :8080  # Go bridge
lsof -i :8081  # Baileys bridge

# Should show LISTEN status
```

**2. Test HTTP connectivity**:
```bash
curl http://localhost:8080/health
curl http://localhost:8081/health

# Should return JSON health status
```

**3. Check firewall**:
```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Linux (ufw)
sudo ufw status

# Windows
# Check Windows Defender Firewall settings
```

**4. Check bridge logs for errors**:
- Look at terminal output where bridges are running
- Look for port binding errors or crash messages

**5. Restart bridges**:
```bash
# Stop
pkill -f "main.go"
pkill -f "baileys-bridge"

# Start fresh
cd whatsapp-bridge && go run main.go &
cd baileys-bridge && npm run dev &
```

**Verification**:
```bash
# Unified MCP should now connect
# In Python/MCP client:
backend_status()
# Should return: {"overall_status": "healthy"}
```

---

### 12. Unified MCP Cannot Connect to Go Bridge

**Symptoms**:
- Baileys bridge works fine
- Go bridge process running
- Tools using Go bridge return `CONNECTION_ERROR`
- `backend_status()` shows Go bridge unhealthy

**Diagnosis**:
Unified MCP configured with wrong Go bridge URL or port.

**Solution**:

**1. Verify Go bridge is running**:
```bash
curl http://localhost:8080/health
# Should return: {"status":"healthy"}
```

**2. Check unified-mcp configuration**:
```python
# Edit unified-mcp/backends/go_client.py
# Verify:
GO_BRIDGE_URL = "http://localhost:8080"  # Correct port?
```

**3. Check for port conflicts**:
```bash
lsof -i :8080
# Should only show Go bridge process
```

**4. Restart unified MCP**:
```bash
# If running via Claude Desktop: Restart Claude Desktop
# If running manually: Restart the MCP server process
```

**Verification**:
```python
backend_status()
# Should show: "go_bridge": {"healthy": true}
```

---

### 13. Messages in Baileys But Not in Go Database

**Symptoms**:
- `get_baileys_sync_status()` shows messages synced
- `get_message_statistics()` shows 0 or low message count
- History sync appears complete but queries return no results

**Diagnosis**:
Messages retrieved by Baileys but not synced to Go database.

**Solution**:

**1. Check Baileys sync status**:
```python
status = get_baileys_sync_status()
print(f"Baileys has {status['messages_synced']} messages")
```

**2. Manually trigger sync**:
```python
result = sync_history_to_database()
print(f"Synced {result['messages_added']} new messages")
print(f"Skipped {result['messages_deduplicated']} duplicates")
```

**3. Verify sync completed**:
```python
stats = get_message_statistics()
print(f"Go database now has {stats['total_messages']} messages")
```

**4. Check for sync errors**:
```python
# If result shows failures:
if result['chats_failed'] > 0:
    print(f"⚠️ {result['chats_failed']} chats failed to sync")
    # Check bridge logs for specific errors
```

**Verification**:
```python
stats = get_message_statistics()
# Should show message count matching Baileys sync count
```

---

### 14. Sync Stalls at High Message Count

**Symptoms**:
- History sync starts but never completes
- Progress stuck at same percentage for >10 minutes
- `get_baileys_sync_status()` shows `is_syncing: true` but no progress

**Diagnosis**:
Baileys sync stalled due to network issues, rate limiting, or memory constraints.

**Solution**:

**1. Cancel stalled sync**:
```python
# For community sync
cancel_sync(chat_jid="community_or_chat_jid")
```

**2. Check Baileys logs**:
- Look for rate limit errors
- Look for memory warnings
- Look for network timeout errors

**3. Wait before retrying**:
```bash
# WhatsApp may be rate limiting
# Wait 15-30 minutes before retry
```

**4. Retry with smaller batches**:
```python
# Instead of full history, sync specific chats
fetch_history(
    chat_jid="specific_chat_jid",
    max_messages=1000  # Smaller batch
)
```

**5. Resume from checkpoint**:
```python
# If previous sync was cancelled
resume_sync(chat_jid="chat_jid", max_messages=1000)
```

**Verification**:
```python
status = get_baileys_sync_status()
# Progress should be increasing
# is_latest should eventually become true
```

---

### 15. Duplicate Messages After Sync

**Symptoms**:
- Running `sync_history_to_database()` multiple times creates duplicate messages
- Message queries return same message multiple times
- Message count inflated

**Diagnosis**:
Deduplication logic not working correctly or corrupted checkpoint data.

**Solution**:

**1. Check deduplication stats**:
```python
result = sync_history_to_database()
print(f"Added: {result['messages_added']}")
print(f"Deduplicated: {result['messages_deduplicated']}")
# Second run should show high deduplication, low additions
```

**2. If duplicates exist, clear and re-sync**:
```bash
# WARNING: This deletes all synced messages
# Back up first if needed

# Stop bridges
pkill -f "main.go"
pkill -f "baileys-bridge"

# Delete databases
rm whatsapp-bridge/store/messages.db
rm baileys-bridge/baileys_temp.db

# Restart and re-sync from scratch
```

**3. Clear Baileys temp storage**:
```python
# After successful sync to Go
clear_baileys_temp_data()
```

**Verification**:
```python
# Query for a specific message
messages = query_synced_messages(content="unique_text", limit=10)
# Should return only 1 result, not duplicates
```

---

### 16. Database Corruption

**Symptoms**:
- SQLite errors in bridge logs: "database disk image is malformed"
- Tools return `DATABASE_ERROR`
- Queries fail with "database locked" errors

**Diagnosis**:
SQLite database file corrupted due to crash, improper shutdown, or disk issues.

**Solution**:

**1. Identify which database is corrupted**:
```bash
# Test Go database
sqlite3 whatsapp-bridge/store/messages.db "PRAGMA integrity_check;"

# Test Baileys database
sqlite3 baileys-bridge/baileys_temp.db "PRAGMA integrity_check;"
```

**2. Stop all bridges**:
```bash
pkill -f "main.go"
pkill -f "baileys-bridge"
```

**3. Backup corrupted database**:
```bash
cp whatsapp-bridge/store/messages.db whatsapp-bridge/store/messages.db.backup
```

**4. Attempt repair**:
```bash
# For Go database
sqlite3 whatsapp-bridge/store/messages.db
.recover
.exit

# If recover fails, restore from backup or delete and re-sync
```

**5. If repair fails, fresh start**:
```bash
# Delete corrupted database
rm whatsapp-bridge/store/messages.db

# Restart bridge - will create new database
cd whatsapp-bridge
go run main.go

# Re-sync history
python -c "from whatsapp import retrieve_full_history, sync_history_to_database; retrieve_full_history(); sync_history_to_database()"
```

**Verification**:
```bash
sqlite3 whatsapp-bridge/store/messages.db "PRAGMA integrity_check;"
# Should return: ok
```

---

### 17. Sync Checkpoint Not Updating

**Symptoms**:
- Resume sync always starts from beginning
- `get_sync_status()` shows outdated checkpoint
- Progress lost after cancelling sync

**Diagnosis**:
Checkpoint writes to Go database failing or not committed.

**Solution**:

**1. Check checkpoint table**:
```bash
sqlite3 whatsapp-bridge/store/messages.db "SELECT * FROM sync_checkpoints;"
```

**2. Verify Go database is writable**:
```bash
ls -la whatsapp-bridge/store/messages.db
# Check permissions - should be writable by bridge process
```

**3. Check for database locks**:
```bash
lsof whatsapp-bridge/store/messages.db
# Should only show Go bridge process
```

**4. Clear stale checkpoints and retry**:
```bash
sqlite3 whatsapp-bridge/store/messages.db "DELETE FROM sync_checkpoints WHERE chat_jid='problematic_jid';"
```

**5. Restart Go bridge**:
```bash
pkill -f "main.go"
cd whatsapp-bridge
go run main.go
```

**Verification**:
```python
# Start sync
fetch_history(chat_jid="test_chat", max_messages=100)

# Check checkpoint was created
status = get_sync_status(chat_jid="test_chat")
print(status['checkpoint'])  # Should show valid checkpoint
```

---

## WhatsApp API Issues

### 18. Rate Limiting When Syncing History

**Symptoms**:
- Sync slows down significantly after initial burst
- Baileys logs show "rate limit" warnings
- `get_baileys_sync_status()` shows slow progress

**Diagnosis**:
WhatsApp rate limiting history sync requests to prevent abuse.

**Solution**:

**1. Slow down sync requests**:
- Baileys handles this automatically with backoff
- Just wait - sync will resume at slower pace

**2. Sync during off-peak hours**:
- WhatsApp may have lower rate limits during busy periods
- Try syncing at night or early morning

**3. Sync incrementally**:
```python
# Instead of full history, sync specific important chats first
important_chats = ["chat1_jid", "chat2_jid"]

for chat in important_chats:
    fetch_history(chat_jid=chat, max_messages=1000)
    time.sleep(60)  # Wait between chats
```

**4. Be patient**:
- Rate limits are temporary (usually 15-60 minutes)
- Sync will continue automatically when limit lifts

**Verification**:
```python
# Monitor progress periodically
status = get_baileys_sync_status()
# Progress should increase over time, even if slowly
```

---

### 19. WhatsApp API Returns 503 Error

**Symptoms**:
- Tools return `WHATSAPP_API_ERROR`
- Bridge logs show "503 Service Unavailable"
- Intermittent failures

**Diagnosis**:
WhatsApp servers temporarily unavailable or experiencing issues.

**Solution**:

**1. Check WhatsApp status**:
- Visit https://downdetector.com/status/whatsapp/
- Check Twitter for #WhatsAppDown reports

**2. Wait and retry**:
```python
import time

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")
```

**3. Check your internet connection**:
```bash
ping web.whatsapp.com
curl https://web.whatsapp.com
```

**4. Verify bridge authentication**:
- 503 can also indicate auth issues
- Check if session expired (see [Authentication Expired](#7-authentication-expired-after-20-days))

**Verification**:
```python
# Once WhatsApp recovers, tools should work
backend_status()
# Should show: {"overall_status": "healthy"}
```

---

### 20. Messages Not Loading

**Symptoms**:
- `list_messages()` returns empty results
- `query_synced_messages()` returns 0 messages
- `get_message_statistics()` shows 0 total messages

**Diagnosis**:
No messages in database - either not synced yet or sync failed.

**Solution**:

**1. Check if history was synced**:
```python
stats = get_message_statistics()
print(f"Messages in database: {stats['total_messages']}")
```

**2. If zero, run initial sync**:
```python
# Step 1: Retrieve history via Baileys
retrieve_full_history(wait_for_completion=True, timeout=600)

# Step 2: Sync to Go database
sync_result = sync_history_to_database()

# Step 3: Verify
stats = get_message_statistics()
print(f"Now have {stats['total_messages']} messages")
```

**3. Check specific chat has messages**:
```python
messages = list_messages(chat_jid="specific_chat_jid", limit=10)
if not messages:
    print("Chat has no messages in database")
    # Try syncing this specific chat
    fetch_history(chat_jid="specific_chat_jid")
```

**Verification**:
```python
stats = get_message_statistics()
# Should show non-zero message count
# oldest_message and newest_message should be populated
```

---

### 21. Media Download Fails

**Symptoms**:
- `download_media_v2()` returns error
- Error: "Failed to download media from WhatsApp servers"
- Media messages show metadata but content unavailable

**Diagnosis**:
Media may have expired on WhatsApp servers (typically >30 days) or network issue.

**Solution**:

**1. Check message age**:
```python
# Old media (>30-90 days) may be expired
# WhatsApp doesn't store media forever
```

**2. Check network connectivity**:
```bash
# Media downloads require good bandwidth
ping whatsapp.net
curl https://mmg.whatsapp.net  # Media server
```

**3. Retry download**:
```python
# Network issues may be transient
import time

for attempt in range(3):
    try:
        result = download_media_v2(message_id="msg_id")
        break
    except Exception as e:
        if attempt < 2:
            time.sleep(2)
        else:
            raise
```

**4. Check disk space**:
```bash
df -h whatsapp-bridge/store/
# Ensure sufficient space for media download
```

**Verification**:
```python
result = download_media_v2(message_id="msg_id")
# Should return: {"success": true, "file_path": "/path/to/media.jpg"}

# Verify file exists
import os
os.path.exists(result['file_path'])  # Should be True
```

---

## Performance Issues

### 22. Slow Message Queries

**Symptoms**:
- `query_synced_messages()` takes >10 seconds
- `list_messages()` slow with large result sets
- Database queries timeout

**Diagnosis**:
Large database without proper indexing or query optimization needed.

**Solution**:

**1. Use pagination**:
```python
# Instead of querying all messages at once
messages = query_synced_messages(limit=100, offset=0)  # Page 1
messages = query_synced_messages(limit=100, offset=100)  # Page 2
```

**2. Add time filters**:
```python
# Narrow search to recent messages
messages = query_synced_messages(
    after_time="2025-10-01T00:00:00Z",
    limit=100
)
```

**3. Filter by chat**:
```python
# Query specific chat instead of all chats
messages = query_synced_messages(
    chat_jid="specific_chat",
    content="search_term",
    limit=50
)
```

**4. Rebuild database indexes** (if very slow):
```bash
sqlite3 whatsapp-bridge/store/messages.db
REINDEX;
VACUUM;
.exit
```

**5. Exclude media for faster text queries**:
```python
messages = query_synced_messages(
    content="search",
    include_media=False,  # Faster
    limit=100
)
```

**Verification**:
```python
import time
start = time.time()
messages = query_synced_messages(limit=100)
elapsed = time.time() - start
print(f"Query took {elapsed:.2f} seconds")
# Should be <2 seconds for reasonable database size
```

---

### 23. High Memory Usage

**Symptoms**:
- Bridge processes consuming >2GB RAM
- System becoming slow during sync operations
- Out of memory errors in logs

**Diagnosis**:
Large history sync or inefficient message processing.

**Solution**:

**1. Restart bridges periodically**:
```bash
# During long sync operations
pkill -f "baileys-bridge"
cd baileys-bridge
npm run dev
```

**2. Limit sync batch size**:
```python
# Instead of full history
fetch_history(chat_jid="chat", max_messages=1000)  # Smaller batches
```

**3. Clear temp storage after sync**:
```python
# Free memory
clear_baileys_temp_data()
```

**4. Increase system swap** (if limited RAM):
```bash
# Linux
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**5. Monitor memory usage**:
```bash
# Check bridge memory usage
ps aux | grep -E "main.go|baileys-bridge"
# Look at RSS column for memory usage
```

**Verification**:
```bash
# Memory usage should stabilize below 1GB per bridge
top -p $(pgrep -f "main.go")
```

---

### 24. Claude Desktop Timeout Errors

**Symptoms**:
- Claude Desktop shows timeout errors
- Operations like `mark_community_as_read_with_history()` fail with timeout
- Error: "MCP server did not respond in time"

**Diagnosis**:
Long-running operations exceeding Claude Desktop's default timeout (typically 60 seconds).

**Solution**:

**1. Increase operation timeout**:
```python
# For hybrid operations, increase sync_timeout
result = mark_community_as_read_with_history(
    community_jid="community_jid",
    sync_timeout=900  # 15 minutes instead of 5
)
```

**2. Run long operations in background**:
```python
# Instead of waiting in Claude
# 1. Start sync
retrieve_full_history(wait_for_completion=False)

# 2. Monitor progress separately
status = get_baileys_sync_status()
print(f"Progress: {status['progress_percent']}%")

# 3. When complete, sync to database
sync_history_to_database()
```

**3. Increase Claude Desktop timeout** (if configurable):
```json
// In claude_desktop_config.json (if supported)
{
  "mcpServers": {
    "whatsapp": {
      "timeout": 300000  // 5 minutes in milliseconds
    }
  }
}
```

**4. Break operation into steps**:
```python
# Instead of one long operation
# Step 1: Sync history
retrieve_full_history()

# Step 2: Wait and check
# (Come back later or check status)

# Step 3: Sync to database
sync_history_to_database()

# Step 4: Mark as read
mark_community_as_read(community_jid)
```

**Verification**:
```python
# Operation completes successfully without timeout
result = mark_community_as_read_with_history(
    community_jid="community_jid",
    sync_timeout=600
)
# Should return success with all steps completed
```

---

## Diagnostic Commands Reference

### Quick Health Checks

```bash
# Check both bridges
curl http://localhost:8080/health  # Go
curl http://localhost:8081/health  # Baileys

# Check processes
ps aux | grep -E "main.go|baileys-bridge"

# Check ports
lsof -i :8080
lsof -i :8081
```

### Database Inspection

```bash
# Go database schema
sqlite3 whatsapp-bridge/store/messages.db ".schema"

# Count messages
sqlite3 whatsapp-bridge/store/messages.db "SELECT COUNT(*) FROM messages;"

# Count chats
sqlite3 whatsapp-bridge/store/messages.db "SELECT COUNT(*) FROM chats;"

# Check integrity
sqlite3 whatsapp-bridge/store/messages.db "PRAGMA integrity_check;"
```

### Log Analysis

```bash
# View bridge output (if running in background)
tail -f /tmp/go-bridge.log
tail -f /tmp/baileys-bridge.log

# Search for errors
grep -i error /tmp/go-bridge.log
grep -i error /tmp/baileys-bridge.log
```

### Network Diagnostics

```bash
# Test WhatsApp connectivity
ping web.whatsapp.com
curl https://web.whatsapp.com

# Check DNS
nslookup web.whatsapp.com

# Test media server
curl https://mmg.whatsapp.net
```

---

## Getting Help

If issues persist after following troubleshooting steps:

### 1. Gather Diagnostic Information

```bash
# System info
uname -a  # OS version
go version
node --version
python3 --version

# Bridge status
curl http://localhost:8080/health
curl http://localhost:8081/health

# Process info
ps aux | grep -E "main.go|baileys-bridge"

# Recent logs (last 50 lines)
tail -50 /path/to/bridge/logs
```

### 2. Run Diagnostic Script

```python
# Save as diagnose.py
from whatsapp import backend_status, get_message_statistics, get_baileys_sync_status

print("=== WhatsApp MCP Diagnostics ===\n")

# Check backends
status = backend_status()
print(f"Overall Status: {status['overall_status']}")
print(f"Go Bridge: {'✅' if status['go_bridge']['healthy'] else '❌'}")
print(f"Baileys Bridge: {'✅' if status['baileys_bridge']['healthy'] else '❌'}")

# Check messages
stats = get_message_statistics()
print(f"\nTotal Messages: {stats['total_messages']}")
print(f"Total Chats: {stats['total_chats']}")

# Check sync
baileys = get_baileys_sync_status()
print(f"\nBaileys Connected: {baileys['connected']}")
print(f"Syncing: {baileys['is_syncing']}")
print(f"Messages Synced: {baileys['messages_synced']}")
```

### 3. Report Issues

**GitHub Issues**: https://github.com/lharries/whatsapp-mcp/issues

**Include in report**:
1. Diagnostic output (from above)
2. Error messages (full text)
3. Steps to reproduce
4. Bridge logs (relevant portions)
5. Operating system and versions
6. Whether issue is reproducible

### 4. Community Support

- **Discord**: (Link if available)
- **Discussions**: GitHub Discussions tab
- **Stack Overflow**: Tag with `whatsapp-mcp`

---

## Additional Resources

- **Setup Guide**: [README.md](./README.md)
- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Architecture Details**: [HYBRID_ARCHITECTURE.md](./HYBRID_ARCHITECTURE.md)
- **Error Handling**: [docs/ERROR_HANDLING.md](./docs/ERROR_HANDLING.md)
- **Common Patterns**: [docs/COMMON_PATTERNS.md](./docs/COMMON_PATTERNS.md)

---

**Last Updated**: 2025-10-12
**Version**: 1.0
**Feedback**: Report inaccuracies or suggest improvements via GitHub Issues
