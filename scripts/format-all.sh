#!/usr/bin/env bash
# Code formatting automation script for WhatsApp MCP project
# Runs: ruff (Python), prettier (JS/TS), gofmt (Go)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🎨 Formatting All Code..."
echo "================================================================"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FORMATTERS_RUN=0

# 1. Python - ruff format
if command -v ruff &> /dev/null; then
    echo "📝 Formatting Python code (ruff)..."
    ruff format unified-mcp/
    ((FORMATTERS_RUN++))
else
    echo -e "${YELLOW}⚠️  Skipping Python formatting (ruff not installed)${NC}"
fi

# 2. TypeScript/JavaScript - prettier
if command -v prettier &> /dev/null; then
    echo "📝 Formatting TypeScript/JavaScript code (prettier)..."
    if [ -d "baileys-bridge/src" ]; then
        prettier --write "baileys-bridge/src/**/*.{ts,js,json}"
        ((FORMATTERS_RUN++))
    else
        echo -e "${YELLOW}⚠️  Skipping baileys-bridge formatting (src/ not found)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping TypeScript formatting (prettier not installed)${NC}"
fi

# 3. Go - gofmt
if command -v gofmt &> /dev/null; then
    echo "📝 Formatting Go code (gofmt)..."
    if [ -d "whatsapp-bridge" ]; then
        gofmt -w whatsapp-bridge/*.go 2>/dev/null || true
        ((FORMATTERS_RUN++))
    else
        echo -e "${YELLOW}⚠️  Skipping whatsapp-bridge formatting (directory not found)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping Go formatting (gofmt not installed)${NC}"
fi

# 4. Markdown - prettier (if available)
if command -v prettier &> /dev/null; then
    echo "📝 Formatting Markdown files (prettier)..."
    prettier --write "**/*.md" 2>/dev/null || true
fi

# Summary
echo ""
echo "================================================================"
echo -e "${GREEN}✅ Formatting complete! ($FORMATTERS_RUN formatters run)${NC}"
echo ""
echo "💡 Tip: Run 'git diff' to review formatting changes"
