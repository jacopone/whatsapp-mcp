"""Backend client implementations for WhatsApp bridges.

This subpackage provides HTTP client interfaces to the WhatsApp backend bridges:
- Go bridge (whatsmeow) on port 8080
- Baileys bridge (Baileys.js) on port 8081

Modules:
    go_client: Go bridge (whatsmeow) HTTP client operations
    baileys_client: Baileys bridge HTTP client operations
    health: Backend health monitoring and status checks

Usage:
    from unified_mcp.backends import go_client, baileys_client, health
"""

# Import backend modules for package access
from . import baileys_client, go_client, health

# Export public API
__all__ = [
    "baileys_client",
    "go_client",
    "health",
]
