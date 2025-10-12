"""WhatsApp MCP unified server package.

This package provides a unified Model Context Protocol (MCP) interface for
WhatsApp operations, coordinating between Go (whatsmeow) and Baileys backends.

Main modules:
    main: MCP server entry point with tool definitions
    constants: Configuration constants and magic number definitions
    backends: Backend client implementations (go_client, baileys_client, health)
    routing: Request routing logic with fallback support
    sync: Database synchronization between backends

Usage:
    Run as module:
        python -m unified_mcp.main

    Import in code:
        from unified_mcp import backends, routing, sync
"""

# Version information
__version__ = "0.1.0"

# Package exports
from . import backends
from . import routing
from . import sync

__all__ = ["backends", "routing", "sync", "__version__"]
