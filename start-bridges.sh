#!/usr/bin/env bash
# Start both WhatsApp bridges for the hybrid MCP architecture

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting WhatsApp MCP Bridges..."
echo

# Check for port conflicts
echo "🔍 Checking for port conflicts..."
GO_PORT_CONFLICT=$(lsof -ti :8080 2>/dev/null || echo "")
BAILEYS_PORT_CONFLICT=$(lsof -ti :8081 2>/dev/null || echo "")

if [ -n "$GO_PORT_CONFLICT" ] || [ -n "$BAILEYS_PORT_CONFLICT" ]; then
    echo "⚠️  Port conflict detected!"
    [ -n "$GO_PORT_CONFLICT" ] && echo "   Port 8080 in use by PID: $GO_PORT_CONFLICT"
    [ -n "$BAILEYS_PORT_CONFLICT" ] && echo "   Port 8081 in use by PID: $BAILEYS_PORT_CONFLICT"
    echo ""
    echo "💡 Options:"
    echo "   1. Run './cleanup-bridges.sh' to kill conflicting processes"
    echo "   2. Run './diagnose-bridges.sh' for detailed diagnostics"
    echo ""
    read -p "Kill conflicting processes now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🧹 Cleaning up..."
        for PID in $GO_PORT_CONFLICT $BAILEYS_PORT_CONFLICT; do
            kill -9 $PID 2>/dev/null || true
        done
        sleep 1
        echo "✅ Cleanup complete"
    else
        echo "❌ Cannot start with ports in use. Exiting."
        exit 1
    fi
fi
echo

# Ensure we're in the devenv
cd /home/guyfawkes/birthday-manager
eval "$(devenv print-dev-env)"
cd "$SCRIPT_DIR"

# Start Go Bridge
echo "Starting Go Bridge (port 8080)..."
cd whatsapp-bridge
./whatsapp-bridge > whatsapp-bridge.log 2>&1 &
GO_PID=$!
echo "✅ Go Bridge started (PID: $GO_PID)"
echo

# Start Baileys Bridge
echo "Starting Baileys Bridge (port 8081)..."
cd ../baileys-bridge
npm start > baileys-bridge.log 2>&1 &
BAILEYS_PID=$!
echo "✅ Baileys Bridge started (PID: $BAILEYS_PID)"
echo

# Save PIDs
echo "$GO_PID" > /tmp/whatsapp-go-bridge.pid
echo "$BAILEYS_PID" > /tmp/whatsapp-baileys-bridge.pid

echo "📝 Bridge PIDs saved to /tmp/"
echo
echo "To stop bridges, run: ./stop-bridges.sh"
echo "To view logs:"
echo "  - Go Bridge: tail -f whatsapp-bridge/whatsapp-bridge.log"
echo "  - Baileys Bridge: tail -f baileys-bridge/baileys-bridge.log"
echo
echo "🔗 Bridges are now running and ready for MCP connections"
