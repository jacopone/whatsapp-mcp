#!/usr/bin/env bash
# Forcefully cleanup all WhatsApp MCP bridge processes
# Use this when diagnose-bridges.sh finds port conflicts or orphaned processes

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 WhatsApp MCP Bridge Cleanup${NC}"
echo "================================"
echo ""

CLEANED=0

# Function to kill processes on a port
kill_port() {
    local PORT=$1
    local NAME=$2

    echo -e "${BLUE}Checking port $PORT ($NAME)...${NC}"

    PIDS=$(lsof -ti :$PORT 2>/dev/null || echo "")

    if [ -n "$PIDS" ]; then
        echo -e "${YELLOW}  Found process(es) using port $PORT:${NC}"
        ps -p $(echo $PIDS | tr ' ' ',') -o pid,cmd 2>/dev/null | grep -v PID | sed 's/^/    /'

        for PID in $PIDS; do
            echo -e "  ${YELLOW}Killing PID $PID...${NC}"
            kill -9 $PID 2>/dev/null || true
            CLEANED=$((CLEANED + 1))
        done

        # Verify port is free
        sleep 1
        STILL_USED=$(lsof -ti :$PORT 2>/dev/null || echo "")
        if [ -z "$STILL_USED" ]; then
            echo -e "  ${GREEN}✅ Port $PORT is now free${NC}"
        else
            echo -e "  ${RED}❌ Port $PORT still in use (may require sudo)${NC}"
        fi
    else
        echo -e "  ${GREEN}✅ Port $PORT already free${NC}"
    fi

    echo ""
}

# Clean up ports
kill_port 8080 "Go Bridge"
kill_port 8081 "Baileys Bridge"

# Kill any remaining bridge processes by name
echo -e "${BLUE}Checking for orphaned processes by name...${NC}"

ORPHANED_GO=$(pgrep -f "whatsapp-bridge" | grep -v $$ || echo "")
if [ -n "$ORPHANED_GO" ]; then
    echo -e "${YELLOW}  Found whatsapp-bridge process(es): $ORPHANED_GO${NC}"
    for PID in $ORPHANED_GO; do
        kill -9 $PID 2>/dev/null || true
        CLEANED=$((CLEANED + 1))
    done
    echo -e "  ${GREEN}✅ Killed orphaned whatsapp-bridge processes${NC}"
else
    echo -e "  ${GREEN}✅ No orphaned whatsapp-bridge processes${NC}"
fi

ORPHANED_BAILEYS=$(pgrep -f "baileys.*bridge" || echo "")
if [ -n "$ORPHANED_BAILEYS" ]; then
    echo -e "${YELLOW}  Found baileys-bridge process(es): $ORPHANED_BAILEYS${NC}"
    for PID in $ORPHANED_BAILEYS; do
        kill -9 $PID 2>/dev/null || true
        CLEANED=$((CLEANED + 1))
    done
    echo -e "  ${GREEN}✅ Killed orphaned baileys-bridge processes${NC}"
else
    echo -e "  ${GREEN}✅ No orphaned baileys-bridge processes${NC}"
fi

echo ""

# Clean up stale PID files
echo -e "${BLUE}Cleaning up PID files...${NC}"
GO_PID_FILE="/tmp/whatsapp-bridge.pid"
BAILEYS_PID_FILE="/tmp/baileys-bridge.pid"

if [ -f "$GO_PID_FILE" ]; then
    rm -f "$GO_PID_FILE"
    echo -e "  ${GREEN}✅ Removed Go Bridge PID file${NC}"
fi

if [ -f "$BAILEYS_PID_FILE" ]; then
    rm -f "$BAILEYS_PID_FILE"
    echo -e "  ${GREEN}✅ Removed Baileys Bridge PID file${NC}"
fi

echo ""
echo "================================"

if [ $CLEANED -gt 0 ]; then
    echo -e "${GREEN}✅ Cleanup complete! Killed $CLEANED process(es).${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Start fresh: ./start-bridges.sh"
    echo "  2. Verify:      ./check-bridges.sh"
else
    echo -e "${GREEN}✅ No cleanup needed - all ports were already free.${NC}"
fi
