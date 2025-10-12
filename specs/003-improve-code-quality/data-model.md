# Data Model: Code Quality and Maintainability Improvements

**Feature**: Code Quality and Maintainability Improvements
**Branch**: `003-improve-code-quality`
**Date**: 2025-10-12

## Overview

This feature is primarily a **refactoring and code quality improvement** effort. It does not introduce new persistent data structures or database schemas. Instead, it reorganizes existing code into better structures and adds metadata (type annotations, docstrings, constants).

The "entities" in this context are **code organization concepts** rather than data models.

---

## 1. Package Structure (Organizational Entity)

### Description

The Python package structure defines how modules are organized and how they import each other. This is a **structural entity** that exists in the filesystem and Python's import system.

### Structure

```
unified_mcp/                    # Root package
├── __init__.py                 # Package initialization
│   └── Exports: main entry points, version info
│
├── main.py                     # MCP server entry point
│   └── Imports: all modules (using package-relative imports)
│
├── constants.py                # Configuration constants (NEW)
│   └── Exports: All timeout values, URLs, limits
│
├── backends/                   # Backend clients subpackage
│   ├── __init__.py
│   │   └── Exports: GoClient, BaileysClient, check_health
│   ├── go_client.py            # Go bridge HTTP client
│   ├── baileys_client.py       # Baileys bridge HTTP client
│   └── health.py               # Health monitoring
│
├── models/                     # Data models subpackage (if any)
│   └── __init__.py
│
├── routing.py                  # Request routing logic
│   └── Imports: backends.*, constants
│
└── sync.py                     # Database sync logic
    └── Imports: backends.*, constants
```

### Key Attributes

- **Module Path**: Fully qualified Python import path (e.g., `unified_mcp.backends.go_client`)
- **Dependencies**: Other modules this module imports
- **Exports**: Public API symbols (functions, classes, constants)
- **Import Style**: Package-relative (`from . import`) or absolute (`from unified_mcp import`)

### Validation Rules

1. All directories containing `.py` files MUST have `__init__.py`
2. No `sys.path` manipulation anywhere in the codebase
3. All imports MUST use package-relative or absolute package syntax
4. Package MUST be installable via `pip install -e .` without errors
5. All 101 existing tests MUST pass with new import structure

---

## 2. Constants Module (Configuration Entity)

### Description

Central registry of all configuration values, magic numbers, and hardcoded strings. This is a **configuration entity** that exists as a Python module.

### Structure

```python
# unified_mcp/constants.py

from typing import Final

# ============================================================================
# HTTP Timeout Configuration (seconds)
# ============================================================================

DEFAULT_TIMEOUT: Final[int] = 30
"""Default timeout for HTTP requests to backend bridges.

Used for: Standard operations (send message, get contacts, etc.)
Rationale: 30 seconds allows for network latency + backend processing
           while preventing indefinite hangs.
"""

MEDIA_TIMEOUT: Final[int] = 60
"""Timeout for media operations (download, upload).

Used for: Media downloads, file uploads, voice note processing
Rationale: Media operations take longer due to file size. 60 seconds
           accommodates up to 10MB files on slow connections.
"""

SHORT_TIMEOUT: Final[int] = 10
"""Timeout for quick operations expected to complete fast.

Used for: Status checks, metadata queries, simple GET requests
Rationale: Operations with minimal processing should complete quickly.
"""

HEALTH_CHECK_TIMEOUT: Final[int] = 5
"""Timeout for backend health checks.

Used for: Health monitoring, liveness probes
Rationale: Health checks should be fast. If backend takes >5s to respond
           to /health, it's likely unhealthy.
"""

# ============================================================================
# Bridge URL Configuration
# ============================================================================

GO_BRIDGE_URL: Final[str] = "http://localhost:8080"
"""Base URL for Go bridge (whatsmeow).

Port 8080 serves: Community operations, marking messages, media handling
"""

BAILEYS_BRIDGE_URL: Final[str] = "http://localhost:8081"
"""Base URL for Baileys bridge (Baileys.js).

Port 8081 serves: History sync, specific Baileys-only features
"""

# ============================================================================
# Retry Configuration
# ============================================================================

MAX_RETRIES: Final[int] = 3
"""Maximum retry attempts for failed operations.

Used for: Failover logic, transient error recovery
Rationale: 3 retries balances resilience with avoiding extended hangs.
"""

RETRY_DELAY: Final[float] = 1.0
"""Delay between retry attempts (seconds).

Used for: Failover retry logic
Rationale: 1 second delay prevents overwhelming failing backend.
"""

# ============================================================================
# Health Check Configuration
# ============================================================================

HEALTH_CACHE_TTL: Final[int] = 1
"""Health check cache time-to-live (seconds).

Rationale: Caching health status for 1 second prevents excessive health
           checks while keeping status relatively fresh.
"""
```

### Key Attributes

- **Constant Name**: UPPER_SNAKE_CASE identifier
- **Type**: Type annotation (int, str, float, etc.)
- **Value**: The actual constant value
- **Immutability**: `Final` type annotation prevents reassignment
- **Documentation**: Docstring explaining purpose and rationale

### Validation Rules

1. All constants MUST use `Final` type annotation
2. All constants MUST have UPPER_SNAKE_CASE naming
3. Each constant MUST have a docstring explaining its purpose
4. Constants MUST be grouped by category with section headers
5. No magic numbers MUST remain in code outside this module

### Usage Pattern

```python
# Before (with magic numbers)
response = requests.get(url, timeout=30)

# After (with constants)
from unified_mcp.constants import DEFAULT_TIMEOUT
response = requests.get(url, timeout=DEFAULT_TIMEOUT)
```

---

## 3. Type Annotations (Metadata Entity)

### Description

Type hints are **inline metadata** attached to function parameters, return values, and variables. They exist only at development/static analysis time and are ignored at runtime (except for runtime type checkers like Pydantic).

### Structure

```python
from typing import Dict, List, Optional, Any, Protocol

# Simple function with type hints
def send_message(
    chat_jid: str,
    text: str,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """Send text message to WhatsApp chat."""
    ...

# Complex function with Optional and Union
def route_with_fallback(
    operation: str,
    primary_backend: str,
    secondary_backend: str,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """Route operation with automatic fallback."""
    ...

# Protocol for structural typing
class BackendClient(Protocol):
    """Protocol defining backend client interface."""
    def send_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]: ...
    def check_health(self) -> bool: ...
```

### Key Attributes

- **Parameter Types**: Type of each function parameter
- **Return Type**: Type returned by function
- **Optional Types**: Parameters/returns that can be None
- **Complex Types**: Dict, List, Union, Protocol, TypedDict

### Validation Rules

1. All public functions MUST have complete type annotations
2. All function parameters MUST have type hints
3. All function return values MUST have type hints
4. Use `Optional[T]` for values that can be None
5. Use `Dict[str, Any]` for JSON-like responses (avoid bare `dict`)
6. Mypy strict mode MUST pass with zero errors

### Common Type Patterns

```python
# JSON response from backend
ResponseDict = Dict[str, Any]

# Optional return value
def get_contact(jid: str) -> Optional[Dict[str, Any]]: ...

# List of items
def get_contacts() -> List[Dict[str, Any]]: ...

# Union for multiple possible types
from typing import Union
def parse_timeout(value: Union[int, str]) -> int: ...
```

---

## 4. Docstrings (Documentation Entity)

### Description

Docstrings are **structured documentation** attached to functions, classes, and modules. They follow Google-style format and include executable examples.

### Structure (Google Style)

```python
def route_with_fallback(
    operation: str,
    primary_backend: str,
    secondary_backend: str,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """Route operation with automatic fallback on failure.

    Attempts to execute operation on primary backend first. If primary fails
    (timeout, connection error, or HTTP error), automatically retries on
    secondary backend. This provides resilience for critical operations.

    Args:
        operation: Operation name (e.g., "SEND_MESSAGE", "GET_CONTACTS").
        primary_backend: Backend to try first ("go" or "baileys").
        secondary_backend: Backend to use if primary fails.
        timeout: Request timeout in seconds. Defaults to DEFAULT_TIMEOUT (30s).

    Returns:
        Response dict from successful backend, or None if both fail.
        Response structure varies by operation type.

    Raises:
        ValueError: If operation name is invalid or unsupported.
        ConnectionError: If both backends are unreachable.

    Examples:
        Send message with fallback:

        >>> result = route_with_fallback(
        ...     operation="SEND_MESSAGE",
        ...     primary_backend="go",
        ...     secondary_backend="baileys",
        ...     timeout=30
        ... )
        >>> if result:
        ...     print(f"Message sent via {result['backend']}")

        Get contacts with automatic retry:

        >>> contacts = route_with_fallback(
        ...     operation="GET_CONTACTS",
        ...     primary_backend="baileys",
        ...     secondary_backend="go"
        ... )
    """
```

### Key Sections

1. **Short Description**: One-line summary (first line)
2. **Long Description**: Detailed explanation (optional, after blank line)
3. **Args**: All parameters with descriptions
4. **Returns**: Return value description
5. **Raises**: Exceptions that can be raised
6. **Examples**: Executable code examples (tested with doctest)

### Validation Rules

1. All public functions MUST have docstrings
2. Docstrings MUST follow Google style (ruff D-series rules)
3. Args section MUST document all parameters
4. Returns section MUST describe return value
5. Raises section MUST list all exceptions raised
6. Examples MUST be executable and pass doctest
7. Examples MUST use `>>>` prompt for Python code

### Ruff Docstring Rules (D-series)

Enabled rules:
- **D100-D107**: Missing docstrings (module, class, function, etc.)
- **D200-D215**: Docstring formatting (quotes, whitespace, etc.)
- **D300-D302**: Docstring content (imperative mood, period, etc.)
- **D400-D417**: Args/Returns/Raises documentation

---

## 5. Complexity Metrics (Quality Entity)

### Description

Cyclomatic complexity is a **code quality metric** measuring the number of linearly independent paths through code. Enforced by ruff's McCabe checker (C90).

### Calculation

Complexity = edges - nodes + 2 (in control flow graph)

**Practical counting**:
- Start at 1
- +1 for each: if, elif, for, while, except, and, or
- +1 for each ternary operator
- +1 for each comprehension with if clause

### Examples

```python
# Complexity = 1 (simple function)
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

# Complexity = 3 (if/elif/else)
def classify(value: int) -> str:
    """Classify value as low/medium/high."""
    if value < 10:
        return "low"
    elif value < 100:
        return "medium"
    else:
        return "high"

# Complexity = 11 (VIOLATES limit of 10)
def complex_routing(operation, backend_status, retry_count, fallback):
    """Too complex - needs refactoring."""
    if operation == "SEND":
        if backend_status["go"]["healthy"]:
            if retry_count < 3:
                return call_go()
            elif fallback:
                return call_baileys()
            else:
                raise Error()
        elif backend_status["baileys"]["healthy"]:
            if retry_count < 3:
                return call_baileys()
            else:
                return None
    else:
        # ... more nested conditions
        pass
```

### Refactoring Strategy

When function exceeds complexity 10:

1. **Extract nested conditionals** into separate functions
2. **Use early returns** to reduce nesting
3. **Create lookup tables** for complex if/elif chains
4. **Use polymorphism** instead of type checking

```python
# Refactored version (complexity = 2 per function)
def route_operation(operation: str, backend_status: Dict, retry_count: int) -> Any:
    """Route operation to healthy backend."""
    backend = select_backend(backend_status)
    return execute_with_retry(backend, operation, retry_count)

def select_backend(backend_status: Dict) -> str:
    """Select healthy backend."""
    if backend_status["go"]["healthy"]:
        return "go"
    return "baileys"

def execute_with_retry(backend: str, operation: str, retry_count: int) -> Any:
    """Execute operation with retry logic."""
    if retry_count >= 3:
        raise MaxRetriesExceeded()
    return call_backend(backend, operation)
```

### Validation Rules

1. All functions MUST have complexity ≤ 10
2. Ruff C90 check MUST pass (`ruff check --select C90`)
3. Functions exceeding limit MUST be refactored before merge
4. Use `# noqa: C901` ONLY with justification comment

---

## Entity Relationships

```
Package Structure
├── Contains → Modules
│   ├── main.py
│   │   ├── Imports → all subpackages
│   │   ├── Contains → MCP tool functions
│   │   │   └── Have → Type Annotations, Docstrings
│   │   └── Uses → Constants
│   │
│   ├── constants.py
│   │   └── Defines → All configuration values
│   │
│   ├── backends/
│   │   ├── go_client.py
│   │   ├── baileys_client.py
│   │   └── health.py
│   │       └── Each Contains → Functions
│   │           ├── Have → Type Annotations
│   │           ├── Have → Docstrings
│   │           ├── Use → Constants
│   │           └── Must Pass → Complexity Check (≤10)
│   │
│   ├── routing.py
│   │   └── Contains → Routing functions
│   │       └── [same as above]
│   │
│   └── sync.py
│       └── Contains → Sync functions
│           └── [same as above]
│
└── Validated By → Tools
    ├── mypy → Checks Type Annotations
    ├── ruff (D-series) → Checks Docstrings
    └── ruff (C90) → Checks Complexity
```

---

## Data Flows

### 1. Import Flow (Package Structure)

```
main.py entry point
    ↓
imports unified_mcp.backends
    ↓
backends/__init__.py
    ↓
exports go_client, baileys_client, health functions
    ↓
main.py can use backend functions directly
```

**Before** (with sys.path hack):
```python
import sys
sys.path.insert(0, '../whatsapp-mcp-server')
from whatsapp import search_contacts  # Breaks IDE, fragile
```

**After** (with proper package):
```python
from unified_mcp.backends import go_client
from unified_mcp.constants import DEFAULT_TIMEOUT
# IDE works, tests work, deployment works
```

### 2. Constants Usage Flow

```
constants.py defines values
    ↓
modules import constants
    ↓
functions use constants instead of magic numbers
    ↓
all timeouts/URLs centralized
```

**Example**:
```python
# constants.py
DEFAULT_TIMEOUT: Final[int] = 30

# go_client.py
from unified_mcp.constants import DEFAULT_TIMEOUT

def send_message(text: str) -> Dict[str, Any]:
    response = requests.post(url, json=data, timeout=DEFAULT_TIMEOUT)
```

### 3. Type Checking Flow

```
Developer writes code with type hints
    ↓
mypy analyzes code statically
    ↓
reports type errors before runtime
    ↓
CI/CD blocks merge if mypy fails
```

### 4. Documentation Flow

```
Developer writes function
    ↓
adds Google-style docstring with examples
    ↓
ruff validates docstring completeness
    ↓
doctest validates examples are executable
    ↓
IDE shows docstring on hover/autocomplete
```

---

## State Transitions

This feature does not introduce stateful entities. All changes are structural/organizational.

**Code Quality States**:
1. **Initial**: sys.path hacks, magic numbers, no types, missing docs
2. **Package Structured**: Proper imports, still has magic numbers
3. **Constants Extracted**: Centralized config, still no types
4. **Type Annotated**: Full type hints, mypy passing
5. **Linted**: All ruff rules passing, complexity ≤10
6. **Documented**: Complete docstrings with examples
7. **Final**: All quality gates passing, maintainability improved

---

## Validation Summary

| Entity | Validation Method | Tool | Success Criteria |
|--------|------------------|------|------------------|
| Package Structure | Import test | pytest | All tests pass without sys.path hacks |
| Package Structure | Module execution | python -m | `python -m unified_mcp.main` runs |
| Constants | Magic number search | grep/ruff | Zero hardcoded timeouts/URLs |
| Type Annotations | Static type check | mypy --strict | Zero mypy errors |
| Docstrings | Docstring validation | ruff D-series | All public functions documented |
| Docstrings | Example validation | doctest | All examples execute successfully |
| Complexity | Complexity check | ruff C90 | All functions ≤10 complexity |
| Overall | Full lint | ruff | Zero warnings across all rules |

---

## Conclusion

This feature refactors code **structure** and adds **metadata** without changing runtime behavior. The "data model" is organizational (package structure, constants module) rather than persistent data. Success is measured by static analysis tools (mypy, ruff) and existing test suite (101 tests).

**Key Deliverables**:
1. ✅ Proper package structure with __init__.py files
2. ✅ constants.py module with all configuration values
3. ✅ Complete type annotations on all functions
4. ✅ Google-style docstrings with executable examples
5. ✅ All functions with complexity ≤10

All changes are **backward compatible** and **testable** with existing test suite.
