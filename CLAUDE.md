# WhatsApp MCP Server

> MCP Server: Personal WhatsApp integration for Claude via web multidevice API

## Overview

This MCP server enables Claude to search, read, and send WhatsApp messages by connecting to your personal WhatsApp account via the whatsmeow Go library. Messages are stored locally in SQLite.

## Tech Stack
- **Bridge**: Go (whatsmeow library)
- **MCP Server**: Python (MCP SDK)
- **Transport**: stdio
- **Storage**: SQLite (local)

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│  whatsapp-mcp-server │────▶│  whatsapp-bridge│
│  (.mcp.json)    │stdio│  (Python MCP)        │     │  (Go/whatsmeow) │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
                                                            │
                                                            ▼
                                                     ┌──────────────┐
                                                     │ WhatsApp Web │
                                                     │ Multi-device │
                                                     └──────────────┘
```

## Quick Start

```bash
# 1. Start the Go bridge (first time requires QR scan)
cd whatsapp-bridge && go run main.go

# 2. Configure in .mcp.json (Claude Code spawns server automatically)
```

## MCP Tools Provided

| Tool | Description |
|------|-------------|
| `search_contacts` | Find contacts by name or phone |
| `list_messages` | Retrieve messages with filters |
| `list_chats` | List available chats |
| `send_message` | Send text to contact/group |
| `send_file` | Send images, videos, documents |
| `send_audio_message` | Send voice messages (requires ffmpeg for conversion) |
| `download_media` | Download media from messages |

## Key Files

| File | Purpose |
|------|---------|
| `whatsapp-mcp-server/main.py` | MCP server entry point |
| `whatsapp-bridge/main.go` | Go bridge to WhatsApp API |
| `whatsapp-bridge/store/` | SQLite database location |

## Debugging

1. Start bridge: `cd whatsapp-bridge && go run main.go`
2. Check QR code scan if first run
3. Verify database populated: `sqlite3 whatsapp-bridge/store/messages.db ".tables"`
4. Check MCP server logs in Claude Code

## Important Notes

- Re-authentication may be needed after ~20 days
- Message history sync can take several minutes after first auth
- Subject to "lethal trifecta" security concerns (prompt injection)

---

## User Memory

<!-- USER_MEMORY_START -->
<!-- USER_MEMORY_END -->
