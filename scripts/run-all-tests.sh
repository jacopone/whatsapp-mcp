#!/usr/bin/env bash
# Test automation script for WhatsApp MCP project
# Runs tests for all three backends: Go, TypeScript, Python

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🧪 Running All Tests..."
echo "================================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

# Function to run tests for a backend
run_backend_tests() {
    local backend_name="$1"
    local backend_dir="$2"
    shift 2

    echo ""
    echo "📦 Testing: $backend_name"
    echo "   Directory: $backend_dir"

    if [ ! -d "$backend_dir" ]; then
        echo -e "${YELLOW}⚠️  Skipping $backend_name (directory not found)${NC}"
        return
    fi

    pushd "$backend_dir" > /dev/null

    if "$@"; then
        echo -e "${GREEN}✅ $backend_name tests PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $backend_name tests FAILED${NC}"
        ((TESTS_FAILED++))
    fi

    popd > /dev/null
}

# 1. Go Bridge Tests
run_backend_tests "Go Bridge" "whatsapp-bridge" go test -v ./... -cover

# 2. Baileys Bridge Tests (TypeScript)
if [ -f "baileys-bridge/package.json" ]; then
    run_backend_tests "Baileys Bridge" "baileys-bridge" npm test
else
    echo -e "${YELLOW}⚠️  Skipping Baileys Bridge (package.json not found)${NC}"
fi

# 3. Unified MCP Tests (Python)
if [ -f "unified-mcp/pyproject.toml" ]; then
    run_backend_tests "Python MCP" "unified-mcp" pytest --cov --cov-report=term
elif [ -f "unified-mcp/requirements.txt" ]; then
    run_backend_tests "Python MCP" "unified-mcp" pytest
else
    echo -e "${YELLOW}⚠️  Skipping Python MCP (no pyproject.toml or requirements.txt)${NC}"
fi

# 4. Integration Tests
if [ -d "tests" ]; then
    echo ""
    echo "📦 Testing: Integration Tests"
    if pytest tests/ -v; then
        echo -e "${GREEN}✅ Integration tests PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ Integration tests FAILED${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  Skipping Integration Tests (tests/ directory empty)${NC}"
fi

# Summary
echo ""
echo "================================================================"
echo "📊 Test Summary"
echo "   Passed: $TESTS_PASSED"
echo "   Failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED test suite(s) failed${NC}"
    exit 1
fi
