#!/usr/bin/env bash
# Stop WhatsApp bridges

echo "🛑 Stopping WhatsApp MCP Bridges..."
echo

# Stop Go Bridge
if [ -f /tmp/whatsapp-go-bridge.pid ]; then
    GO_PID=$(cat /tmp/whatsapp-go-bridge.pid)
    if kill -0 "$GO_PID" 2>/dev/null; then
        kill "$GO_PID"
        echo "✅ Go Bridge stopped (PID: $GO_PID)"
    else
        echo "⚠️  Go Bridge not running"
    fi
    rm /tmp/whatsapp-go-bridge.pid
else
    echo "⚠️  No Go Bridge PID file found"
fi

# Stop Baileys Bridge
if [ -f /tmp/whatsapp-baileys-bridge.pid ]; then
    BAILEYS_PID=$(cat /tmp/whatsapp-baileys-bridge.pid)
    if kill -0 "$BAILEYS_PID" 2>/dev/null; then
        kill "$BAILEYS_PID"
        echo "✅ Baileys Bridge stopped (PID: $BAILEYS_PID)"
    else
        echo "⚠️  Baileys Bridge not running"
    fi
    rm /tmp/whatsapp-baileys-bridge.pid
else
    echo "⚠️  No Baileys Bridge PID file found"
fi

echo
echo "All bridges stopped"
