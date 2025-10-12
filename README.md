# WhatsApp MCP Server - Hybrid Architecture

A Model Context Protocol (MCP) server for WhatsApp that combines the best of two powerful libraries:
- **Go/whatsmeow**: Communities support, reliable messaging, mark-as-read functionality
- **Baileys**: Comprehensive history sync, business catalog features

This hybrid architecture gives you **maximum WhatsApp functionality** through a unified MCP interface that AI agents like Claude can use to interact with your personal WhatsApp account.

![WhatsApp MCP](./example-use.png)

> **🔒 Privacy First**: All messages stored locally in SQLite. Data only sent to LLM when you explicitly use MCP tools.

> **⚠️ Security Note**: As with many MCP servers, the WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). Project injection could lead to private data exfiltration.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Full Installation Guide](#full-installation-guide)
  - [Prerequisites](#prerequisites)
  - [Step 1: Clone Repository](#step-1-clone-repository)
  - [Step 2: Start Go Bridge (Port 8080)](#step-2-start-go-bridge-port-8080)
  - [Step 3: Start Baileys Bridge (Port 8081)](#step-3-start-baileys-bridge-port-8081)
  - [Step 4: Configure Unified MCP Server](#step-4-configure-unified-mcp-server)
  - [Step 5: Restart Your AI Client](#step-5-restart-your-ai-client)
- [Usage Examples](#usage-examples)
- [Available MCP Tools (75 Total)](#available-mcp-tools-75-total)
- [Hybrid Operations Explained](#hybrid-operations-explained)
- [Documentation](#documentation)
  - [Example Workflows](#example-workflows)
  - [API Reference](#api-reference)
  - [Troubleshooting](#troubleshooting)
- [Windows Compatibility](#windows-compatibility)
- [Technical Details](#technical-details)
- [Project Structure](#project-structure)
- [Feature Coverage Matrix](#feature-coverage-matrix)
- [Contributing](#contributing)
- [Security & Privacy](#security--privacy)
- [Links](#links)
- [License](#license)

---

## Quick Start

**Prerequisites**: Go 1.24+, Node.js 20+, Python 3.12+, UV package manager

```bash
# 1. Clone repository
git clone https://github.com/lharries/whatsapp-mcp.git
cd whatsapp-mcp

# 2. Start Go bridge (port 8080)
cd whatsapp-bridge
go run main.go
# → Scan QR code #1 with WhatsApp

# 3. Start Baileys bridge (port 8081) - in new terminal
cd baileys-bridge
npm install && npm run dev
# → Scan QR code #2 with WhatsApp

# 4. Configure Claude Desktop / Cursor (see full setup below)
```

Once configured, ask Claude: *"List my recent WhatsApp chats"* to verify it's working!

---

## Architecture Overview

The hybrid system consists of **three components** working together:

```
┌─────────────────────────────────────────────────┐
│       AI Agent (Claude, Cursor, etc.)           │
└────────────────────┬────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────┐
│    Unified MCP Orchestrator (Python)            │
│    - Routes requests to optimal backend         │
│    - Synchronizes databases                     │
│    - Exposes 75 MCP tools                       │
└─────────┬──────────────────────┬────────────────┘
          │ HTTP :8080           │ HTTP :8081
┌─────────▼─────────┐   ┌────────▼──────────────┐
│   Go Bridge       │   │  Baileys Bridge       │
│   (whatsmeow)     │   │  (@whiskeysockets)    │
│                   │   │                       │
│ ✓ Communities     │   │ ✓ History Sync        │
│ ✓ Mark as Read    │   │ ✓ Business Catalog    │
│ ✓ Send Messages   │   │                       │
└─────────┬─────────┘   └────────┬──────────────┘
          │ SQLite               │ SQLite (temp)
┌─────────▼─────────┐   ┌────────▼──────────────┐
│   messages.db     │◄──┤  baileys_temp.db      │
│ (SINGLE SOURCE    │sync│  (Temporary for       │
│  OF TRUTH)        │   │   history sync)       │
└───────────────────┘   └───────────────────────┘
```

### Why Hybrid?

| Feature | Go/whatsmeow | Baileys | Unified (Best of Both) |
|---------|--------------|---------|------------------------|
| History Sync | ❌ Broken | ✅ Excellent | ✅ Via Baileys |
| Communities | ✅ Full Support | ❌ Not Supported | ✅ Via Go |
| Mark as Read | ✅ Full Support | ✅ Basic | ✅ Via Go |
| Send Messages | ✅ Good | ✅ Good | ✅ Via Go |
| Business Catalog | ❌ None | ✅ Full | ✅ Via Baileys |

**Result**: 95%+ feature coverage instead of 60-70% with a single library!

---

## Full Installation Guide

### Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| Go | 1.24+ | [golang.org/dl](https://golang.org/dl/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| UV | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| FFmpeg | Optional | For audio conversion (voice messages) |

**Platform Notes**:
- **Windows**: See [Windows Setup](#windows-compatibility) for CGO configuration
- **macOS**: All prerequisites available via Homebrew
- **Linux**: Use your package manager (apt, dnf, pacman)

### Step 1: Clone Repository

```bash
git clone https://github.com/lharries/whatsapp-mcp.git
cd whatsapp-mcp
```

### Step 2: Start Go Bridge (Port 8080)

The Go bridge handles most operations (communities, messaging, mark-as-read):

```bash
cd whatsapp-bridge
go run main.go
```

**First-time setup**:
1. A QR code will appear in your terminal
2. Open WhatsApp on your phone → Settings → Linked Devices
3. Tap "Link a Device" and scan the QR code
4. Bridge will connect and start syncing recent messages

**Note**: Authentication lasts ~20 days, then you'll need to re-scan.

The Go bridge will:
- ✅ Connect to WhatsApp Web API
- ✅ Store messages in `whatsapp-bridge/store/messages.db`
- ✅ Listen on `http://localhost:8080`

### Step 3: Start Baileys Bridge (Port 8081)

The Baileys bridge provides history sync and business features:

**In a new terminal**:

```bash
cd whatsapp-mcp/baileys-bridge
npm install
npm run dev
```

**First-time setup**:
1. Another QR code will appear (different from Go bridge)
2. Open WhatsApp → Settings → Linked Devices
3. Scan this QR code (you'll now have 2 linked devices)
4. Bridge will connect and be ready for history sync

The Baileys bridge will:
- ✅ Connect to WhatsApp as second device
- ✅ Store temp data in `baileys-bridge/baileys_temp.db`
- ✅ Listen on `http://localhost:8081`

### Step 4: Configure Unified MCP Server

The Python orchestrator routes requests to the right bridge and exposes tools to AI agents.

#### For Claude Desktop

Create or edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/absolute/path/to/whatsapp-mcp/unified-mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

**Find paths**:
- UV path: Run `which uv` (macOS/Linux) or `where uv` (Windows)
- Absolute path: Run `pwd` in the `whatsapp-mcp/unified-mcp` directory

#### For Cursor

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/absolute/path/to/whatsapp-mcp/unified-mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

### Step 5: Restart Your AI Client

- **Claude Desktop**: Completely quit and reopen
- **Cursor**: Restart the editor

You should now see WhatsApp tools available! Try asking:
- "List my recent WhatsApp chats"
- "Show me my last 5 messages with [contact name]"
- "Mark all messages in [community name] as read"

---

## Usage Examples

### Basic Messaging

```
You: Send a message to John saying "Hey, are we still on for lunch?"
Claude: [Uses send_text_message_v2 tool]
```

### Community Management

```
You: Mark all messages in "Family Group" community as read
Claude: [Uses mark_community_as_read_with_history tool - hybrid operation!]
```

### History Sync + Search

```
You: Find all messages mentioning "project deadline" in the last month
Claude: [Uses retrieve_full_history then query_synced_messages]
```

---

## Available MCP Tools (75 Total)

The unified MCP server provides 75 tools across 10 categories:

| Category | Tools | Backend | Key Functions |
|----------|-------|---------|---------------|
| **Messaging** | 15 | Go | send, edit, delete, react, forward, download media |
| **Contacts** | 9 | Go | search, profile, status management |
| **Chats** | 13 | Go | list, archive, pin, mute, mark as read |
| **Communities** | 4 | Go + Hybrid | list, get groups, mark all as read |
| **History Sync** | 9 | Baileys + Hybrid | retrieve full history, sync to database |
| **Message Query** | 4 | Go | list, search, context, statistics |
| **Privacy** | 8 | Go | block contacts, privacy settings |
| **Business** | 3 | Baileys | profile, catalog (Baileys-exclusive) |
| **Newsletters** | 5 | Go | subscribe, create, react to posts |
| **Backend Status** | 2 | Both | Health checks for both bridges |

**Total**: 75 tools providing comprehensive WhatsApp functionality

For detailed tool documentation, see [API_REFERENCE.md](./API_REFERENCE.md).

---

## Hybrid Operations Explained

Some operations automatically combine both bridges for maximum functionality:

### mark_community_as_read_with_history()

**Problem**: Communities may have thousands of historical messages that Go bridge never synced.

**Hybrid Solution**:
1. Check Go database for messages in community groups
2. If history missing → Trigger Baileys history sync
3. Wait for sync completion
4. Sync Baileys temp DB → Go messages.db
5. Use Go bridge to mark all as read
6. Return unified result

**User Experience**: Single command, automatic hybrid orchestration!

---

## Documentation

### Example Workflows

We've created detailed example guides to help you get started:

- **[Basic Messaging](./docs/examples/basic-messaging.md)** - 10 examples covering:
  - Send text, images, voice notes, locations, contacts
  - Edit/delete messages, reactions, forwarding
  - Download media files
  - Error handling patterns

- **[Community Management](./docs/examples/community-management.md)** - 10 examples covering:
  - List communities and groups
  - Mark all messages as read (with/without history sync)
  - Monitor unread counts
  - Search across communities
  - Bulk operations (archive, mute)

- **[Hybrid Operations](./docs/examples/hybrid-operations.md)** - 10 examples covering:
  - Full history retrieval workflow
  - Database synchronization
  - Resume interrupted syncs
  - Business catalog browsing
  - System health checks

### API Reference

Complete documentation for all 75 MCP tools:
- [API_REFERENCE.md](./API_REFERENCE.md) - Full tool reference with parameters, return values, examples, and error codes
- [BACKEND_ROUTING.md](./docs/BACKEND_ROUTING.md) - Routing decision tree explaining which backend handles each operation
- [COMMON_PATTERNS.md](./docs/COMMON_PATTERNS.md) - Common usage patterns combining multiple tools
- [ERROR_HANDLING.md](./docs/ERROR_HANDLING.md) - Error codes, resolution steps, and handling patterns

### Troubleshooting

### Quick Diagnostics

Check if both bridges are running:

```bash
# Check Go bridge
curl http://localhost:8080/health

# Check Baileys bridge
curl http://localhost:8081/health

# Check processes
ps aux | grep -E "main.go|baileys-bridge"
```

### Common Issues

#### Port Already in Use

**Symptom**: Bridge fails to start with `EADDRINUSE` error

**Solution**:
```bash
# Find process using port 8080 or 8081
lsof -i :8080
lsof -i :8081

# Kill the process
kill -9 <PID>
```

#### QR Code Not Appearing

**Symptom**: No QR code shown in terminal

**Causes**:
- Terminal doesn't support QR rendering → Try a different terminal
- Already authenticated → Check for "Already logged in" message
- Previous session crashed → Delete `store/` directory and restart

#### Authentication Expired

**Symptom**: "Session expired" or connection errors after ~20 days

**Solution**:
```bash
# Stop bridges
# Delete session files
rm -rf whatsapp-bridge/store/whatsapp.db
rm -rf baileys-bridge/auth_info_baileys/

# Restart bridges and re-scan QR codes
```

#### Database Sync Issues

**Symptom**: Messages appear in Baileys but not in Go database

**Solution**:
```bash
# Manually trigger sync (via MCP tool)
sync_history_to_database()

# Check sync status
get_sync_checkpoints()
```

For more detailed troubleshooting with 24 common issues and solutions, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## Windows Compatibility

**CGO Requirement**: The Go bridge requires CGO to be enabled for SQLite support.

### Setup Steps

1. **Install C Compiler**:
   - Download and install [MSYS2](https://www.msys2.org/)
   - Add `C:\msys64\ucrt64\bin` to your PATH
   - Full guide: [VS Code C++ on Windows](https://code.visualstudio.com/docs/cpp/config-mingw)

2. **Enable CGO and Run**:
   ```bash
   cd whatsapp-bridge
   go env -w CGO_ENABLED=1
   go run main.go
   ```

**Common Error**: `Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work.`
**Fix**: Follow steps above to enable CGO.

---

## Technical Details

### Data Flow

1. **AI Agent** sends request via MCP protocol (stdio)
2. **Unified MCP** routes to appropriate backend:
   - Go bridge (56 tools): Communities, messaging, contacts, chats
   - Baileys bridge (10 tools): History sync, business catalog
   - Hybrid (2 tools): Operations combining both
3. **Bridges** communicate with WhatsApp Web API
4. **Data** stored in SQLite databases
5. **Responses** flow back through the chain to AI agent

### Database Architecture

- **messages.db** (Go): Single source of truth for all messages
- **baileys_temp.db** (Baileys): Temporary storage for history sync
- **Sync Process**: Copies messages from Baileys → Go with deduplication
- **Schema**: Go schema is authoritative, Baileys transforms to match

### Message Handling

- **Real-time**: Captured by Go bridge → immediate database write
- **Historical**: Retrieved by Baileys → temp storage → synced to Go
- **Search**: All queries go to Go database (unified access)

---

## Project Structure

```
whatsapp-mcp/
├── whatsapp-bridge/          # Go bridge (port 8080)
│   ├── main.go               # Entry point
│   ├── routes/               # HTTP API routes
│   └── store/                # SQLite databases
│       └── messages.db       # Message storage
├── baileys-bridge/           # Baileys bridge (port 8081)
│   ├── src/main.ts           # Entry point
│   └── baileys_temp.db       # Temp history storage
├── unified-mcp/              # Python MCP orchestrator
│   ├── main.py               # MCP server with 75 tools
│   ├── backends/             # Go and Baileys clients
│   ├── routing.py            # Smart routing logic
│   └── sync.py               # Database sync
└── docs/                     # Documentation
    ├── examples/             # Practical usage examples
    │   ├── basic-messaging.md
    │   ├── community-management.md
    │   └── hybrid-operations.md
    ├── BACKEND_ROUTING.md    # Routing decision tree
    ├── COMMON_PATTERNS.md    # Usage patterns
    └── ERROR_HANDLING.md     # Error reference
```

---

## Feature Coverage Matrix

| Feature Category | Go Bridge | Baileys Bridge | Hybrid | Result |
|------------------|-----------|----------------|--------|--------|
| **Messaging** | | | | |
| Send text/media | ✅ | ✅ | ✅ Go | Primary via Go |
| Edit/delete messages | ✅ | ✅ | ✅ Go | Primary via Go |
| React to messages | ✅ | ✅ | ✅ Go | Primary via Go |
| Forward messages | ✅ | ✅ | ✅ Go | Primary via Go |
| **Contacts** | | | | |
| Search contacts | ✅ | ✅ | ✅ Go | Primary via Go |
| Profile management | ✅ | ✅ | ✅ Go | Primary via Go |
| **Chats** | | | | |
| List/manage chats | ✅ | ✅ | ✅ Go | Primary via Go |
| Archive/pin/mute | ✅ | ❌ | ✅ Go | Only via Go |
| Mark as read | ✅ | ✅ | ✅ Go | Better via Go |
| **Communities** | | | | |
| List communities | ✅ | ❌ | ✅ Go | Only via Go |
| Get groups | ✅ | ❌ | ✅ Go | Only via Go |
| Mark all as read | ✅ | ❌ | ✅ Hybrid | Hybrid operation |
| **History** | | | | |
| Sync full history | ❌ | ✅ | ✅ Baileys | Only via Baileys |
| Query synced | ✅ | ✅ | ✅ Go | Via Go DB |
| **Business** | | | | |
| View catalog | ❌ | ✅ | ✅ Baileys | Only via Baileys |
| Product details | ❌ | ✅ | ✅ Baileys | Only via Baileys |
| **Privacy** | | | | |
| Block contacts | ✅ | ✅ | ✅ Go | Primary via Go |
| Privacy settings | ✅ | ✅ | ✅ Go | Primary via Go |

**Overall Coverage**: 95%+ of WhatsApp functionality vs. 60-70% with single library

---

## Contributing

See [docs/CONTRIBUTING.md](./docs/CONTRIBUTING.md) for documentation contribution guidelines.

## Security & Privacy

- **Local storage**: All data in SQLite, no cloud sync
- **Controlled access**: LLM only sees data via MCP tools you invoke
- **Two devices**: Both bridges show as separate linked devices in WhatsApp
- **E2E encryption**: WhatsApp's end-to-end encryption maintained
- **No data collection**: No telemetry or analytics sent anywhere

## Links

### Documentation
- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md) - Complete tool reference
- **Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - 24 common issues and solutions
- **Example Workflows**:
  - [Basic Messaging](./docs/examples/basic-messaging.md)
  - [Community Management](./docs/examples/community-management.md)
  - [Hybrid Operations](./docs/examples/hybrid-operations.md)
- **Technical Guides**:
  - [Backend Routing](./docs/BACKEND_ROUTING.md)
  - [Common Patterns](./docs/COMMON_PATTERNS.md)
  - [Error Handling](./docs/ERROR_HANDLING.md)

### External Resources
- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Go/whatsmeow**: [github.com/tulir/whatsmeow](https://github.com/tulir/whatsmeow)
- **Baileys**: [github.com/WhiskeySockets/Baileys](https://github.com/WhiskeySockets/Baileys)

## License

[Check repository for license information]

---

**Questions or Issues?**
1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - 24 common issues with solutions
2. Review [Example Workflows](./docs/examples/) - Copy-paste ready code
3. See [API Reference](./API_REFERENCE.md) - Complete tool documentation
4. [GitHub Issues](https://github.com/lharries/whatsapp-mcp/issues)
5. [MCP Protocol Docs](https://modelcontextprotocol.io/quickstart/server)
