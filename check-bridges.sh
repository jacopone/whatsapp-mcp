#!/usr/bin/env bash
# Check WhatsApp bridge status

echo "🔍 Checking WhatsApp MCP Bridge Status..."
echo

# Check Go Bridge
echo "Go Bridge (port 8080):"
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || echo "{}")
    echo "  ✅ Running and healthy"
    echo "  Response: $HEALTH"
else
    echo "  ❌ Not responding"
fi
echo

# Check Baileys Bridge
echo "Baileys Bridge (port 8081):"
if curl -s http://localhost:8081/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8081/health | python3 -m json.tool 2>/dev/null || echo "{}")
    echo "  ✅ Running and healthy"
    echo "  Response: $HEALTH"
else
    echo "  ❌ Not responding"
fi
echo

# Check PIDs
echo "Process Status:"
if [ -f /tmp/whatsapp-go-bridge.pid ]; then
    GO_PID=$(cat /tmp/whatsapp-go-bridge.pid)
    if kill -0 "$GO_PID" 2>/dev/null; then
        echo "  Go Bridge PID: $GO_PID (running)"
    else
        echo "  Go Bridge PID: $GO_PID (not running)"
    fi
else
    echo "  Go Bridge: No PID file"
fi

if [ -f /tmp/whatsapp-baileys-bridge.pid ]; then
    BAILEYS_PID=$(cat /tmp/whatsapp-baileys-bridge.pid)
    if kill -0 "$BAILEYS_PID" 2>/dev/null; then
        echo "  Baileys Bridge PID: $BAILEYS_PID (running)"
    else
        echo "  Baileys Bridge PID: $BAILEYS_PID (not running)"
    fi
else
    echo "  Baileys Bridge: No PID file"
fi
