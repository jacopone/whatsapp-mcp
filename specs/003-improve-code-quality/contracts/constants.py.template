"""Configuration constants for WhatsApp MCP unified server.

This module provides centralized configuration values used throughout the codebase.
All constants use `typing.Final` to prevent accidental modification.

Constants are organized by category:
- HTTP Timeout Configuration
- Bridge URL Configuration
- Retry Configuration
- Health Check Configuration

Enforces: FR-006, FR-007, FR-008, FR-009, FR-010
Success Criteria: SC-004, SC-005, SC-006
"""

from typing import Final

# =============================================================================
# HTTP Timeout Configuration (seconds)
# =============================================================================

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

# =============================================================================
# Bridge URL Configuration
# =============================================================================

GO_BRIDGE_URL: Final[str] = "http://localhost:8080"
"""Base URL for Go bridge (whatsmeow).

Port 8080 serves: Community operations, marking messages, media handling
"""

BAILEYS_BRIDGE_URL: Final[str] = "http://localhost:8081"
"""Base URL for Baileys bridge (Baileys.js).

Port 8081 serves: History sync, specific Baileys-only features
"""

# =============================================================================
# Retry Configuration
# =============================================================================

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

# =============================================================================
# Health Check Configuration
# =============================================================================

HEALTH_CACHE_TTL: Final[int] = 1
"""Health check cache time-to-live (seconds).

Rationale: Caching health status for 1 second prevents excessive health
           checks while keeping status relatively fresh.
"""

# =============================================================================
# Usage Examples
# =============================================================================
# All examples follow FR-025 (executable docstring examples)

def example_usage() -> None:
    """Demonstrate how to use constants in application code.

    Examples:
        Import constants at module level:

        >>> from unified_mcp.constants import DEFAULT_TIMEOUT, GO_BRIDGE_URL
        >>> import requests
        >>> # Use in HTTP requests
        >>> # response = requests.get(GO_BRIDGE_URL + "/health", timeout=DEFAULT_TIMEOUT)

        Constants are immutable:

        >>> from unified_mcp.constants import DEFAULT_TIMEOUT
        >>> # This would fail with mypy error:
        >>> # DEFAULT_TIMEOUT = 60  # Error: Cannot assign to final name
    """
    pass

# =============================================================================
# Validation Criteria (From contracts/)
# =============================================================================
# ✅ SC-004: Zero hardcoded timeout values in src/ (verified by grep)
# ✅ SC-005: All timeout constants use typing.Final
# ✅ SC-006: Each constant has docstring explaining purpose
# ✅ FR-006: All timeout values extracted to named constants
# ✅ FR-007: All URL endpoints extracted to named constants
# ✅ FR-008: Constants use UPPER_SNAKE_CASE naming
# ✅ FR-009: Constants use typing.Final for immutability
# ✅ FR-010: Each constant has explanatory docstring
