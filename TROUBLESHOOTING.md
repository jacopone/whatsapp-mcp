# WhatsApp MCP Troubleshooting Guide

## 🚨 Quick Fix for Common Issues

### Problem: "Offline Mode - WhatsApp MCP Unavailable"

**One-liner fix:**
```bash
cd whatsapp-mcp && ./cleanup-bridges.sh && ./start-bridges.sh
```

This will:
1. Kill any orphaned processes
2. Free up ports 8080 and 8081
3. Start fresh bridge instances

---

## 📋 Diagnostic Commands

### 1. **Full System Diagnostics**
```bash
cd whatsapp-mcp
./diagnose-bridges.sh
```

**What it checks:**
- ✅ Port conflicts (8080, 8081)
- ✅ PID file vs actual processes
- ✅ Bridge health endpoints
- ✅ Log files for errors
- ✅ Orphaned processes

### 2. **Force Cleanup**
```bash
cd whatsapp-mcp
./cleanup-bridges.sh
```

**What it does:**
- Kills ALL processes using ports 8080 and 8081
- Removes stale PID files
- Finds and kills orphaned bridge processes

### 3. **Status Check**
```bash
cd whatsapp-mcp
./check-bridges.sh
```

**Shows:** Bridge health, WhatsApp connection status, process PIDs

---

## 🔧 Common Issues & Solutions

### Issue 1: Port Already in Use

**Symptoms:** `bind: address already in use`

**Solution:**
```bash
cd whatsapp-mcp
./cleanup-bridges.sh
./start-bridges.sh
```

### Issue 2: WhatsApp Not Connected

**Solution:**
```bash
# Check logs for QR code
tail -f whatsapp-mcp/whatsapp-bridge/whatsapp-bridge.log
# Scan QR code with WhatsApp mobile app
```

---

## 🔑 Quick Command Reference

| Task | Command |
|------|---------|
| **Full diagnostics** | `./diagnose-bridges.sh` |
| **Force cleanup** | `./cleanup-bridges.sh` |
| **Start bridges** | `./start-bridges.sh` |
| **Stop bridges** | `./stop-bridges.sh` |
| **Check status** | `./check-bridges.sh` |
| **View Go logs** | `tail -f whatsapp-bridge/whatsapp-bridge.log` |
| **View Baileys logs** | `tail -f baileys-bridge/baileys-bridge.log` |
