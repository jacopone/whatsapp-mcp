# Implementation Quickstart: Code Quality and Maintainability Improvements

**Feature**: Code Quality and Maintainability Improvements
**Branch**: `003-improve-code-quality`
**Date**: 2025-10-12

## Overview

This guide provides step-by-step instructions for implementing the code quality improvements. Follow the phases in order to minimize risk and ensure all tests continue passing throughout the refactoring.

**Total estimated time**: 23-31 hours
**Approach**: 5 phases, each independently testable

---

## Prerequisites

Before starting implementation:

1. **Checkout feature branch**:
   ```bash
   git checkout 003-improve-code-quality
   ```

2. **Verify all tests pass**:
   ```bash
   cd unified-mcp
   pytest
   # Expected: All 101 tests pass
   ```

3. **Install development dependencies**:
   ```bash
   # Add mypy to dev dependencies
   # Already have: pytest, ruff
   pip install -e ".[dev]"
   ```

4. **Backup current state**:
   ```bash
   git commit -am "Pre-refactoring checkpoint"
   ```

---

## Phase 1: Package Structure (US1)

**Estimated time**: 4-6 hours
**Priority**: P1 (Must complete before other phases)
**Success Criteria**: SC-001, SC-002, SC-003

### Step 1.1: Create Package Structure

```bash
cd unified-mcp

# Create __init__.py files
touch __init__.py
touch backends/__init__.py
touch models/__init__.py  # If models directory exists
```

### Step 1.2: Update Root Package __init__.py

Create `unified-mcp/__init__.py`:
```python
"""WhatsApp MCP unified server package.

This package provides a unified MCP interface for WhatsApp operations,
coordinating between Go (whatsmeow) and Baileys backends.
"""

from . import backends
from . import routing
from . import sync

__all__ = ["backends", "routing", "sync"]
```

### Step 1.3: Update Backends Package __init__.py

Create `unified-mcp/backends/__init__.py` using template from `contracts/__init__.py.template`:
```python
"""Backend client implementations for WhatsApp bridges."""

from .go_client import (
    # Export all public functions from go_client
)
from .baileys_client import (
    # Export all public functions from baileys_client
)
from .health import check_backend_health

__all__ = [
    # List all exported functions
]
```

### Step 1.4: Remove sys.path Hack

Edit `unified-mcp/main.py`:
```python
# BEFORE:
import sys
sys.path.insert(0, '../whatsapp-mcp-server')
from whatsapp import search_contacts

# AFTER:
from unified_mcp.backends import search_contacts
```

### Step 1.5: Update All Import Statements

Search for absolute imports and convert to package-relative:
```bash
# Find all Python imports
rg "^import " --type py
rg "^from " --type py

# Common patterns to fix:
# OLD: from whatsapp import X
# NEW: from unified_mcp.backends import X

# OLD: from routing import route_operation
# NEW: from unified_mcp.routing import route_operation
```

### Step 1.6: Validate Phase 1

```bash
# Test 1: Module execution
python -m unified_mcp.main
# Expected: Server starts without import errors

# Test 2: All tests pass
pytest
# Expected: All 101 tests pass

# Test 3: Package installation
pip install -e .
# Expected: No errors

# Test 4: Verify no sys.path manipulation
rg "sys\.path" --type py
# Expected: Zero matches
```

**Checkpoint**: Commit working state
```bash
git add .
git commit -m "US1: Implement proper package structure with __init__.py files

- Add __init__.py to all package directories
- Remove sys.path.insert hack from main.py
- Convert all imports to package-relative syntax
- All 101 tests passing

Enforces: FR-001 to FR-005
Success: SC-001 to SC-003"
```

---

## Phase 2: Constants Extraction (US2)

**Estimated time**: 2-3 hours
**Priority**: P2 (Can run after US1)
**Success Criteria**: SC-004, SC-005, SC-006

### Step 2.1: Create Constants Module

Copy template and customize:
```bash
cp specs/003-improve-code-quality/contracts/constants.py.template \
   unified-mcp/constants.py
```

Review and ensure all values match current codebase.

### Step 2.2: Identify All Magic Numbers

```bash
# Find timeout values
rg "timeout\s*=\s*\d+" --type py

# Find URL strings
rg "http://localhost:\d+" --type py

# Find retry counts
rg "retry|retries" -i --type py
```

Document findings and map to constants.

### Step 2.3: Replace Magic Numbers in go_client.py

```python
# BEFORE:
response = requests.post(url, json=data, timeout=30)

# AFTER:
from unified_mcp.constants import DEFAULT_TIMEOUT
response = requests.post(url, json=data, timeout=DEFAULT_TIMEOUT)
```

Process all timeout values:
- `timeout=30` → `DEFAULT_TIMEOUT`
- `timeout=60` → `MEDIA_TIMEOUT`
- `timeout=10` → `SHORT_TIMEOUT`
- `timeout=5` → `HEALTH_CHECK_TIMEOUT`

### Step 2.4: Replace URL Strings

```python
# BEFORE:
url = "http://localhost:8080" + "/api/send"

# AFTER:
from unified_mcp.constants import GO_BRIDGE_URL
url = GO_BRIDGE_URL + "/api/send"
```

### Step 2.5: Replace in Other Modules

Repeat steps 2.3-2.4 for:
- `baileys_client.py`
- `routing.py`
- `sync.py`
- `health.py`

### Step 2.6: Validate Phase 2

```bash
# Test 1: No magic numbers remain
rg "timeout\s*=\s*[0-9]+" --type py unified-mcp/
# Expected: Zero matches (except in constants.py and tests)

rg "http://localhost" --type py unified-mcp/
# Expected: Zero matches (except in constants.py and tests)

# Test 2: All tests pass
pytest
# Expected: All 101 tests pass (behavior unchanged)

# Test 3: Verify Final usage
mypy constants.py --strict
# Expected: No errors about Final reassignment
```

**Checkpoint**: Commit working state
```bash
git add .
git commit -m "US2: Extract magic numbers to centralized constants module

- Create constants.py with all configuration values
- Replace hardcoded timeouts with named constants
- Replace hardcoded URLs with named constants
- Use typing.Final for immutability
- All tests passing, behavior unchanged

Enforces: FR-006 to FR-010
Success: SC-004 to SC-006"
```

---

## Phase 3: Type Annotations (US3)

**Estimated time**: 6-8 hours
**Priority**: P3 (Can run after US1 and US2)
**Success Criteria**: SC-007, SC-008, SC-009

### Step 3.1: Configure Mypy

Add to `unified-mcp/pyproject.toml` (merge with existing):
```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_reexport = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "fastmcp.*"
ignore_missing_imports = true
```

### Step 3.2: Run Initial Mypy Check

```bash
mypy unified-mcp/ --strict
# Expected: Many errors about missing type annotations
# Note line numbers and files
```

### Step 3.3: Add Type Hints to routing.py

Priority module (complex logic):
```python
# BEFORE:
def route_with_fallback(operation, primary_backend, secondary_backend, timeout=30):
    # ...

# AFTER:
from typing import Dict, Any, Optional
from unified_mcp.constants import DEFAULT_TIMEOUT

def route_with_fallback(
    operation: str,
    primary_backend: str,
    secondary_backend: str,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    # ...
```

### Step 3.4: Add Type Hints to Backend Clients

Process `go_client.py` and `baileys_client.py`:
```python
# Common patterns:
def send_message(chat_jid: str, text: str) -> Dict[str, Any]:
    # ...

def get_contacts(limit: int = 20) -> List[Dict[str, Any]]:
    # ...

def check_health() -> bool:
    # ...
```

### Step 3.5: Add Type Hints to Remaining Modules

Process in order:
1. `sync.py` (database sync logic)
2. `health.py` (monitoring)
3. `main.py` (MCP tool functions)

### Step 3.6: Validate Phase 3

```bash
# Test 1: Mypy passes
mypy unified-mcp/ --strict
# Expected: Zero errors

# Test 2: Count annotations
rg "def .+\(" --type py unified-mcp/ | wc -l
rg "def .+\(.+\) ->" --type py unified-mcp/ | wc -l
# Expected: >95% of functions have return type annotations

# Test 3: All tests pass
pytest
# Expected: All 101 tests pass (types don't change runtime)
```

**Checkpoint**: Commit working state
```bash
git add .
git commit -m "US3: Add comprehensive type annotations with mypy strict mode

- Configure mypy in pyproject.toml
- Add type hints to all public functions
- Add type hints to all parameters and returns
- Use Optional, Dict, List, Any appropriately
- Mypy strict mode passes with zero errors

Enforces: FR-012 to FR-015
Success: SC-007 to SC-009"
```

---

## Phase 4: Linting and Complexity (US4)

**Estimated time**: 3-4 hours
**Priority**: P4 (Can run after US3)
**Success Criteria**: SC-010, SC-011, SC-012

### Step 4.1: Configure Ruff

Add to `unified-mcp/pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["."]

[tool.ruff.lint]
select = [
    "E", "F", "I", "N", "W", "UP", "C90", "D", "RUF",
]
ignore = [
    "D203", "D213",
]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.isort]
known-first-party = ["unified_mcp"]
```

### Step 4.2: Run Initial Ruff Check

```bash
ruff check unified-mcp/
# Note all errors, especially C901 (complexity)
```

### Step 4.3: Auto-fix Simple Issues

```bash
ruff check --fix unified-mcp/
# Fixes import sorting, formatting, simple style issues
```

### Step 4.4: Identify High-Complexity Functions

```bash
ruff check --select C90 unified-mcp/
# Example output:
# routing.py:45:1: C901 `route_with_retry` is too complex (12 > 10)
```

### Step 4.5: Refactor Complex Functions

For each function with complexity >10:

**Strategy 1: Extract nested logic**
```python
# BEFORE (complexity 12):
def route_with_retry(operation, backend, retry_count):
    if operation == "SEND":
        if backend == "go":
            if retry_count < 3:
                result = call_go()
                if result.success:
                    return result
                elif fallback:
                    return call_baileys()
        # ... more nesting

# AFTER (complexity 3 each):
def route_with_retry(operation: str, backend: str, retry_count: int) -> Any:
    selected_backend = select_backend(backend, retry_count)
    return execute_operation(operation, selected_backend)

def select_backend(backend: str, retry_count: int) -> str:
    if retry_count >= 3:
        raise MaxRetriesError()
    return backend

def execute_operation(operation: str, backend: str) -> Any:
    if operation == "SEND":
        return send_via_backend(backend)
    return get_via_backend(backend)
```

**Strategy 2: Early returns**
```python
# BEFORE (many nested ifs):
def process(data):
    if data.valid:
        if data.ready:
            if data.complete:
                return result

# AFTER (early returns):
def process(data):
    if not data.valid:
        return None
    if not data.ready:
        return None
    if not data.complete:
        return None
    return result
```

### Step 4.6: Validate Phase 4

```bash
# Test 1: Ruff passes all checks
ruff check unified-mcp/
# Expected: Zero warnings

# Test 2: No high-complexity functions
ruff check --select C90 unified-mcp/
# Expected: Zero C901 violations

# Test 3: Imports sorted
ruff check --select I unified-mcp/
# Expected: Zero I001 violations

# Test 4: All tests pass
pytest
# Expected: All 101 tests pass
```

**Checkpoint**: Commit working state
```bash
git add .
git commit -m "US4: Configure comprehensive linting with ruff

- Add ruff configuration with all rule sets
- Fix import sorting issues
- Refactor high-complexity functions (<= 10)
- All ruff checks passing with zero warnings

Enforces: FR-016 to FR-020
Success: SC-010 to SC-012"
```

---

## Phase 5: Documentation (US5)

**Estimated time**: 8-10 hours
**Priority**: P5 (Can run after US3 and US4)
**Success Criteria**: SC-013, SC-014, SC-015

### Step 5.1: Enable Docstring Validation

Already configured in Phase 4 ruff setup (D-series rules).

### Step 5.2: Run Docstring Check

```bash
ruff check --select D unified-mcp/
# Note all missing docstrings and formatting issues
```

### Step 5.3: Add Docstrings to MCP Tool Functions

Priority: 75 MCP tool functions in `main.py`:
```python
def send_message(chat_jid: str, text: str) -> Dict[str, Any]:
    """Send text message to WhatsApp chat.

    Args:
        chat_jid: WhatsApp JID of recipient (format: "123456789@s.whatsapp.net").
        text: Message text to send (max 4096 characters).

    Returns:
        Response dictionary containing:
            - success: bool indicating if send succeeded
            - message_id: str with WhatsApp message ID
            - timestamp: int UNIX timestamp

    Raises:
        ValueError: If chat_jid format is invalid.
        ConnectionError: If backend is unreachable.

    Examples:
        >>> response = send_message("123@s.whatsapp.net", "Hello")
        >>> assert response["success"] is True
    """
    # implementation
```

Use `contracts/docstring.example.py` as reference.

### Step 5.4: Add Docstrings to Internal Functions

Process routing, backend, and sync functions:
- All functions in `routing.py`
- All functions in `go_client.py`
- All functions in `baileys_client.py`
- All functions in `sync.py`
- All functions in `health.py`

### Step 5.5: Add Module Docstrings

Every `.py` file needs module docstring:
```python
"""Module purpose and overview.

This module provides X functionality for Y purpose.
Key features:
- Feature 1
- Feature 2

Typical usage:
    >>> from unified_mcp.module import function
    >>> result = function(args)
"""
```

### Step 5.6: Validate Examples with Doctest

```bash
# Enable doctest in pytest
# (Already configured in contracts/pyproject.toml.template)

pytest --doctest-modules unified-mcp/
# Expected: All examples pass
```

### Step 5.7: Validate Phase 5

```bash
# Test 1: All functions documented
ruff check --select D unified-mcp/
# Expected: Zero D100-D107 violations

# Test 2: Google style followed
ruff check --select D unified-mcp/
# Expected: Zero D400-D417 violations

# Test 3: Examples executable
pytest --doctest-modules unified-mcp/
# Expected: All doctests pass

# Test 4: All tests pass
pytest
# Expected: All 101 tests + doctests pass
```

**Checkpoint**: Commit working state
```bash
git add .
git commit -m "US5: Add comprehensive Google-style docstrings

- Add docstrings to all 75 MCP tool functions
- Add docstrings to all internal functions
- Add module docstrings to all Python files
- Include executable examples in docstrings
- All ruff docstring checks passing
- All doctest examples passing

Enforces: FR-021 to FR-025
Success: SC-013 to SC-015"
```

---

## Final Validation

After completing all 5 phases, run comprehensive validation:

```bash
# 1. Package structure
python -m unified_mcp.main
# Expected: Starts without errors

# 2. All tests pass
pytest
# Expected: All 101 original tests + new doctests pass

# 3. Type checking
mypy unified-mcp/ --strict
# Expected: Zero errors

# 4. Linting
ruff check unified-mcp/
# Expected: Zero warnings

# 5. No magic numbers
rg "timeout\s*=\s*[0-9]+" --type py unified-mcp/
rg "http://localhost" --type py unified-mcp/
# Expected: Zero matches (except constants.py and tests)

# 6. Documentation complete
ruff check --select D unified-mcp/
pytest --doctest-modules unified-mcp/
# Expected: Zero warnings, all doctests pass

# 7. Complexity limits
ruff check --select C90 unified-mcp/
# Expected: All functions <= 10 complexity
```

---

## CI/CD Integration

After merging, the CI/CD pipeline (Feature 002) will enforce these quality gates:

```yaml
# Added to .github/workflows/ci.yml (code-quality job)
- name: Type check
  run: mypy unified-mcp/ --strict

- name: Lint check
  run: ruff check unified-mcp/

- name: Docstring tests
  run: pytest --doctest-modules unified-mcp/
```

All checks must pass before merge to `develop`.

---

## Troubleshooting

### Issue: Import errors after package restructure

**Symptom**: `ModuleNotFoundError: No module named 'unified_mcp'`
**Solution**:
```bash
pip install -e .
# Reinstalls package in development mode
```

### Issue: Tests fail after constants extraction

**Symptom**: Tests use hardcoded values that changed
**Solution**: Update test fixtures to use constants:
```python
from unified_mcp.constants import DEFAULT_TIMEOUT
# Use DEFAULT_TIMEOUT in tests
```

### Issue: Mypy false positives

**Symptom**: Mypy complains about third-party library types
**Solution**: Add to `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = "problematic_library.*"
ignore_missing_imports = true
```

### Issue: Complexity cannot be reduced below 10

**Symptom**: Function is inherently complex (state machine, etc.)
**Solution**: Add justified ignore:
```python
def complex_state_machine(...):  # noqa: C901
    # Justification: State machine requires all transitions in one function
    # for correctness. Breaking apart would reduce clarity.
    ...
```

---

## Success Metrics

Upon completion, verify all 18 success criteria:

**Package Structure** (SC-001 to SC-003):
- ✅ Developer can run `python -m unified_mcp.main`
- ✅ All 101 tests pass without sys.path modifications
- ✅ IDE auto-complete works

**Constants** (SC-004 to SC-006):
- ✅ Zero hardcoded timeout values
- ✅ All constants use typing.Final
- ✅ Each constant has explanatory docstring

**Type Checking** (SC-007 to SC-009):
- ✅ Mypy strict mode passes
- ✅ All public functions have type annotations
- ✅ Type annotation coverage >95%

**Linting** (SC-010 to SC-012):
- ✅ Ruff check exits with code 0
- ✅ All imports correctly sorted
- ✅ No functions with complexity >10

**Documentation** (SC-013 to SC-015):
- ✅ All public functions have docstrings
- ✅ All docstrings follow Google style
- ✅ All docstring examples are executable

**Overall Quality** (SC-016 to SC-018):
- ✅ All 101 existing tests pass
- ✅ 15% maintainability improvement (code metrics)
- ✅ 70% reduction in code review style comments

---

**Implementation Status**: Ready to execute
**Next Command**: `/speckit.tasks` (generates detailed task breakdown)
