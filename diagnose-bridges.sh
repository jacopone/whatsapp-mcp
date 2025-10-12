#!/usr/bin/env bash
# Diagnostic script for WhatsApp MCP bridges
# Detects common issues and provides solutions

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 WhatsApp MCP Bridge Diagnostics${NC}"
echo "=================================="
echo ""

ISSUES_FOUND=0

# Check 1: Port conflicts
echo -e "${BLUE}[1/5] Checking for port conflicts...${NC}"
GO_PORT_USED=$(lsof -ti :8080 2>/dev/null || echo "")
BAILEYS_PORT_USED=$(lsof -ti :8081 2>/dev/null || echo "")

if [ -n "$GO_PORT_USED" ]; then
    echo -e "${YELLOW}  ⚠️  Port 8080 is in use by PID(s): $GO_PORT_USED${NC}"
    ps -p $GO_PORT_USED -o pid,cmd 2>/dev/null | grep -v PID | while read line; do
        echo "      $line"
    done
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}  ✅ Port 8080 is free${NC}"
fi

if [ -n "$BAILEYS_PORT_USED" ]; then
    echo -e "${YELLOW}  ⚠️  Port 8081 is in use by PID(s): $BAILEYS_PORT_USED${NC}"
    ps -p $BAILEYS_PORT_USED -o pid,cmd 2>/dev/null | grep -v PID | while read line; do
        echo "      $line"
    done
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}  ✅ Port 8081 is free${NC}"
fi

echo ""

# Check 2: PID files vs actual processes
echo -e "${BLUE}[2/5] Checking PID files...${NC}"
GO_PID_FILE="/tmp/whatsapp-bridge.pid"
BAILEYS_PID_FILE="/tmp/baileys-bridge.pid"

if [ -f "$GO_PID_FILE" ]; then
    GO_PID=$(cat "$GO_PID_FILE")
    if ps -p "$GO_PID" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ Go Bridge PID file matches running process ($GO_PID)${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Go Bridge PID file exists but process $GO_PID is not running (stale)${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "  ℹ️  No Go Bridge PID file found"
fi

if [ -f "$BAILEYS_PID_FILE" ]; then
    BAILEYS_PID=$(cat "$BAILEYS_PID_FILE")
    if ps -p "$BAILEYS_PID" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ Baileys Bridge PID file matches running process ($BAILEYS_PID)${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Baileys Bridge PID file exists but process $BAILEYS_PID is not running (stale)${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "  ℹ️  No Baileys Bridge PID file found"
fi

echo ""

# Check 3: Bridge health endpoints
echo -e "${BLUE}[3/5] Testing bridge health endpoints...${NC}"
GO_HEALTH=$(curl -s http://localhost:8080/health 2>/dev/null || echo "")
if [ -n "$GO_HEALTH" ]; then
    GO_STATUS=$(echo "$GO_HEALTH" | jq -r '.status' 2>/dev/null || echo "unknown")
    GO_CONNECTED=$(echo "$GO_HEALTH" | jq -r '.whatsapp_connected' 2>/dev/null || echo "unknown")

    if [ "$GO_STATUS" = "healthy" ] || [ "$GO_STATUS" = "degraded" ]; then
        echo -e "${GREEN}  ✅ Go Bridge responding (status: $GO_STATUS, connected: $GO_CONNECTED)${NC}"

        if [ "$GO_CONNECTED" = "false" ]; then
            echo -e "${YELLOW}     ⚠️  WhatsApp not connected - check logs for QR code or auth issues${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    else
        echo -e "${RED}  ❌ Go Bridge unhealthy (status: $GO_STATUS)${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "${RED}  ❌ Go Bridge not responding on port 8080${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

BAILEYS_HEALTH=$(curl -s http://localhost:8081/health 2>/dev/null || echo "")
if [ -n "$BAILEYS_HEALTH" ]; then
    BAILEYS_STATUS=$(echo "$BAILEYS_HEALTH" | jq -r '.status' 2>/dev/null || echo "unknown")
    BAILEYS_CONNECTED=$(echo "$BAILEYS_HEALTH" | jq -r '.connected' 2>/dev/null || echo "unknown")

    if [ "$BAILEYS_STATUS" = "ok" ] || [ "$BAILEYS_STATUS" = "healthy" ]; then
        echo -e "${GREEN}  ✅ Baileys Bridge responding (status: $BAILEYS_STATUS, connected: $BAILEYS_CONNECTED)${NC}"
    else
        echo -e "${RED}  ❌ Baileys Bridge unhealthy (status: $BAILEYS_STATUS)${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "${RED}  ❌ Baileys Bridge not responding on port 8081${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""

# Check 4: Log files
echo -e "${BLUE}[4/5] Checking log files...${NC}"
GO_LOG="whatsapp-bridge/whatsapp-bridge.log"
BAILEYS_LOG="baileys-bridge/baileys-bridge.log"

if [ -f "$GO_LOG" ]; then
    GO_LOG_SIZE=$(stat -f%z "$GO_LOG" 2>/dev/null || stat -c%s "$GO_LOG" 2>/dev/null || echo "0")
    GO_LOG_ERRORS=$(tail -50 "$GO_LOG" 2>/dev/null | grep -i "error" | wc -l || echo "0")

    echo -e "${GREEN}  ✅ Go Bridge log exists (${GO_LOG_SIZE} bytes)${NC}"

    if [ "$GO_LOG_ERRORS" -gt 0 ]; then
        echo -e "${YELLOW}     ⚠️  Found $GO_LOG_ERRORS error(s) in last 50 lines${NC}"
        echo -e "${YELLOW}     Recent errors:${NC}"
        tail -50 "$GO_LOG" | grep -i "error" | tail -3 | sed 's/^/       /'
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "${RED}  ❌ Go Bridge log not found at $GO_LOG${NC}"
fi

if [ -f "$BAILEYS_LOG" ]; then
    BAILEYS_LOG_SIZE=$(stat -f%z "$BAILEYS_LOG" 2>/dev/null || stat -c%s "$BAILEYS_LOG" 2>/dev/null || echo "0")
    echo -e "${GREEN}  ✅ Baileys Bridge log exists (${BAILEYS_LOG_SIZE} bytes)${NC}"
else
    echo -e "${RED}  ❌ Baileys Bridge log not found at $BAILEYS_LOG${NC}"
fi

echo ""

# Check 5: Orphaned processes
echo -e "${BLUE}[5/5] Checking for orphaned bridge processes...${NC}"
ORPHANED_GO=$(pgrep -f "whatsapp-bridge" | grep -v $$ || echo "")
ORPHANED_BAILEYS=$(pgrep -f "baileys-bridge" || echo "")

if [ -n "$ORPHANED_GO" ]; then
    COUNT=$(echo "$ORPHANED_GO" | wc -w)
    if [ "$COUNT" -gt 1 ]; then
        echo -e "${YELLOW}  ⚠️  Found $COUNT whatsapp-bridge processes:${NC}"
        ps -p $(echo $ORPHANED_GO | tr ' ' ',') -o pid,etime,cmd 2>/dev/null | grep -v PID | sed 's/^/       /'
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}  ✅ Only one whatsapp-bridge process running${NC}"
    fi
else
    echo -e "  ℹ️  No whatsapp-bridge processes found"
fi

if [ -n "$ORPHANED_BAILEYS" ]; then
    COUNT=$(echo "$ORPHANED_BAILEYS" | wc -w)
    if [ "$COUNT" -gt 1 ]; then
        echo -e "${YELLOW}  ⚠️  Found $COUNT baileys-bridge processes${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}  ✅ Only one baileys-bridge process running${NC}"
    fi
else
    echo -e "  ℹ️  No baileys-bridge processes found"
fi

echo ""
echo "=================================="

# Summary and recommendations
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ No issues found! Bridges appear healthy.${NC}"
else
    echo -e "${YELLOW}⚠️  Found $ISSUES_FOUND issue(s)${NC}"
    echo ""
    echo -e "${BLUE}🔧 Recommended actions:${NC}"

    if [ -n "$GO_PORT_USED" ] || [ -n "$BAILEYS_PORT_USED" ]; then
        echo -e "  ${YELLOW}1. Port conflicts detected:${NC}"
        echo "     Run: ./cleanup-bridges.sh"
        echo "     This will kill all processes using ports 8080/8081"
        echo ""
    fi

    if [ "$GO_CONNECTED" = "false" ]; then
        echo -e "  ${YELLOW}2. WhatsApp not connected:${NC}"
        echo "     Check logs: tail -f whatsapp-bridge/whatsapp-bridge.log"
        echo "     Look for QR code or authentication errors"
        echo ""
    fi

    echo -e "  ${YELLOW}3. After fixing issues:${NC}"
    echo "     ./stop-bridges.sh && ./start-bridges.sh"
    echo "     ./check-bridges.sh"
fi

echo ""
echo -e "${BLUE}📝 Quick commands:${NC}"
echo "  View logs:        tail -f whatsapp-bridge/whatsapp-bridge.log"
echo "  Force cleanup:    ./cleanup-bridges.sh"
echo "  Restart bridges:  ./stop-bridges.sh && ./start-bridges.sh"
echo "  Check status:     ./check-bridges.sh"
