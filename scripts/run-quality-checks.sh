#!/usr/bin/env bash
# Quality check automation script for WhatsApp MCP project
# Runs: gitleaks, semgrep, lizard, TDD Guard

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔍 Running Quality Checks..."
echo "=" * 80

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CHECKS_PASSED=0
CHECKS_FAILED=0

# Function to run a check and track results
run_check() {
    local check_name="$1"
    shift

    echo ""
    echo "📋 Running: $check_name"
    if "$@"; then
        echo -e "${GREEN}✅ $check_name PASSED${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}❌ $check_name FAILED${NC}"
        ((CHECKS_FAILED++))
    fi
}

# 1. Gitleaks - Secret scanning
run_check "Gitleaks (Secret Scanning)" gitleaks detect --source . --no-git --verbose

# 2. Semgrep - OWASP security rules
if [ -f ".semgrep.yml" ]; then
    run_check "Semgrep (Security)" semgrep --config .semgrep.yml --error
else
    echo -e "${YELLOW}⚠️  Skipping Semgrep (no .semgrep.yml found)${NC}"
fi

# 3. Lizard - Code complexity (CCN < 10)
run_check "Lizard (Complexity)" lizard . -l python -l go -l javascript -l typescript --CCN 10

# 4. TDD Guard - Test presence check
if command -v tdd-guard &> /dev/null; then
    run_check "TDD Guard (Test Coverage)" tdd-guard check
else
    echo -e "${YELLOW}⚠️  Skipping TDD Guard (not installed)${NC}"
fi

# Summary
echo ""
echo "=" * 80
echo "📊 Quality Check Summary"
echo "   Passed: $CHECKS_PASSED"
echo "   Failed: $CHECKS_FAILED"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $CHECKS_FAILED check(s) failed${NC}"
    exit 1
fi
