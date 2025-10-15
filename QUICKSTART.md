# WhatsApp MCP Quick Start Guide

## 🚀 Installation (One-Time Setup)

### 1. Build the Bridges

```bash
cd /home/guyfawkes/birthday-manager/whatsapp-mcp

# Build Go Bridge
cd whatsapp-bridge
eval "$(devenv print-dev-env)"
go build -o whatsapp-bridge *.go
cd ..

# Build Baileys Bridge
cd baileys-bridge
npm install
npm run build
cd ..
```

### 2. Start the Bridges

```bash
cd /home/guyfawkes/birthday-manager/whatsapp-mcp
./start-bridges.sh
```

**First-time setup**: You'll need to scan QR codes for both bridges:
1. Go Bridge QR: `tail -f whatsapp-bridge/whatsapp-bridge.log`
2. Baileys Bridge QR: `tail -f baileys-bridge/baileys-bridge.log`

Scan both QR codes with your WhatsApp mobile app.

### 3. Verify Everything Works

```bash
./check-bridges.sh
```

You should see both bridges responding with healthy status.

### 4. Restart Claude Code

The MCP configuration in `.mcp.json` has been updated. Restart Claude Code to load the new WhatsApp MCP server.

---

## 📱 Daily Usage

### Start Bridges
```bash
cd /home/guyfawkes/birthday-manager/whatsapp-mcp
./start-bridges.sh
```

### Check Status
```bash
./check-bridges.sh
```

### Stop Bridges
```bash
./stop-bridges.sh
```

### View Logs
```bash
# Go Bridge
tail -f whatsapp-bridge/whatsapp-bridge.log

# Baileys Bridge
tail -f baileys-bridge/baileys-bridge.log
```

---

## 🎯 Using WhatsApp MCP in Claude Code

Once Claude Code restarts, you'll have access to **75 WhatsApp tools**:

### Example Commands

**Search contacts:**
```
Search my WhatsApp contacts for "John"
```

**Get messages from a chat:**
```
Get the last 20 messages from the chat with Jane Doe
```

**Mark community as read:**
```
Mark the "Tenuta Larnianone Guests" community as read
```

**Send a message:**
```
Send "Happy birthday!" to John Smith on WhatsApp
```

**Get newsletter info:**
```
Get information about the newsletter with JID 120363...
```

---

## 🔧 Troubleshooting

### Bridge Not Responding
```bash
# Check if processes are running
ps aux | grep whatsapp-bridge
ps aux | grep npm

# Restart bridges
./stop-bridges.sh
./start-bridges.sh
```

### MCP Not Loading
1. Check Claude Code logs: `~/.claude/logs/`
2. Verify `.mcp.json` is correct
3. Ensure bridges are running: `./check-bridges.sh`
4. Restart Claude Code completely

### QR Code Expired
The bridges save authentication sessions. If you need to re-authenticate:
1. Stop bridges: `./stop-bridges.sh`
2. Delete session data:
   - Go: `rm -rf whatsapp-bridge/data/`
   - Baileys: `rm -rf baileys-bridge/auth_info_baileys/`
3. Restart: `./start-bridges.sh`
4. Scan new QR codes

---

## 📊 Available Tools

See `IMPLEMENTATION_STATUS.md` for the complete list of 75 implemented tools across:
- Messaging & Media (23 tools)
- Privacy & Security (9 tools)
- Business Features (3 tools)
- Newsletters (5 tools)
- Communities (4 tools)
- Groups (6 tools)
- Polls & Status (6 tools)
- History Sync (9 tools)
- Database & Health (10 tools)

---

## 🔄 Auto-Start on Boot (Optional)

To have bridges start automatically on system boot, you can create a systemd user service. Let me know if you'd like help with this!
