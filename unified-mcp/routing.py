"""Request routing logic for the unified WhatsApp MCP.

Routes requests to the appropriate backend (Go/whatsmeow or Baileys)
based on availability, health status, and operation requirements.
"""
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, Literal

from backends.health import HealthMonitor, get_health_monitor

logger = logging.getLogger(__name__)

Backend = Literal["go", "baileys"]


class OperationType(Enum):
    """Types of operations that can be routed."""
    # Message operations
    SEND_MESSAGE = "send_message"
    SEND_FILE = "send_file"
    SEND_AUDIO = "send_audio"
    MARK_AS_READ = "mark_as_read"
    DOWNLOAD_MEDIA = "download_media"

    # History sync operations
    SYNC_FULL_HISTORY = "sync_full_history"
    SYNC_CHAT_HISTORY = "sync_chat_history"

    # Community operations
    LIST_COMMUNITIES = "list_communities"
    GET_COMMUNITY_GROUPS = "get_community_groups"
    MARK_COMMUNITY_AS_READ = "mark_community_as_read"

    # Contact operations
    SEARCH_CONTACTS = "search_contacts"
    LIST_CONTACTS = "list_contacts"

    # Chat operations
    LIST_CHATS = "list_chats"
    GET_CHAT = "get_chat"
    LIST_MESSAGES = "list_messages"


class RoutingStrategy(Enum):
    """Routing strategies for different operation types."""
    PRIMARY_ONLY = "primary_only"      # Use primary backend only
    PREFER_GO = "prefer_go"            # Prefer Go, fallback to Baileys
    PREFER_BAILEYS = "prefer_baileys"  # Prefer Baileys, fallback to Go
    ROUND_ROBIN = "round_robin"        # Alternate between backends
    FASTEST = "fastest"                # Use backend with lowest response time


class Router:
    """Routes requests to appropriate backend based on health and requirements."""

    def __init__(self, health_monitor: HealthMonitor | None = None) -> None:
        """Initialize router.

        Args:
            health_monitor: HealthMonitor instance (defaults to global instance)
        """
        self.health_monitor: HealthMonitor = health_monitor or get_health_monitor()
        self.round_robin_counter: int = 0

        # Define routing strategies for each operation type
        self.operation_strategies: dict[OperationType, RoutingStrategy] = {
            # Message operations - prefer Go (more stable)
            OperationType.SEND_MESSAGE: RoutingStrategy.PREFER_GO,
            OperationType.SEND_FILE: RoutingStrategy.PREFER_GO,
            OperationType.SEND_AUDIO: RoutingStrategy.PREFER_GO,
            OperationType.MARK_AS_READ: RoutingStrategy.PREFER_GO,
            OperationType.DOWNLOAD_MEDIA: RoutingStrategy.PREFER_GO,

            # History sync operations - require specific backend
            OperationType.SYNC_FULL_HISTORY: RoutingStrategy.PREFER_BAILEYS,  # Baileys has syncFullHistory
            OperationType.SYNC_CHAT_HISTORY: RoutingStrategy.PREFER_GO,

            # Community operations - prefer Go
            OperationType.LIST_COMMUNITIES: RoutingStrategy.PREFER_GO,
            OperationType.GET_COMMUNITY_GROUPS: RoutingStrategy.PREFER_GO,
            OperationType.MARK_COMMUNITY_AS_READ: RoutingStrategy.PREFER_GO,

            # Contact/chat operations - can use either, prefer Go
            OperationType.SEARCH_CONTACTS: RoutingStrategy.PREFER_GO,
            OperationType.LIST_CONTACTS: RoutingStrategy.PREFER_GO,
            OperationType.LIST_CHATS: RoutingStrategy.PREFER_GO,
            OperationType.GET_CHAT: RoutingStrategy.PREFER_GO,
            OperationType.LIST_MESSAGES: RoutingStrategy.PREFER_GO,
        }

    def _select_with_preference(
        self, preferred: Backend, fallback: Backend, available: list[str], operation_name: str
    ) -> Backend | None:
        """Select backend with preference and fallback.

        Args:
            preferred: The preferred backend
            fallback: The fallback backend if preferred unavailable
            available: List of available backends
            operation_name: Name of operation for logging

        Returns:
            Selected backend or None
        """
        if preferred in available:
            return preferred
        elif fallback in available:
            logger.info(f"{preferred.capitalize()} backend unavailable for {operation_name}, using {fallback.capitalize()}")
            return fallback
        return None

    def _select_fastest_backend(self, overall_health: Any) -> Backend | None:
        """Select the fastest available backend.

        Args:
            overall_health: Overall health status

        Returns:
            Fastest backend or None
        """
        go_backend = overall_health.go_backend
        baileys_backend = overall_health.baileys_backend

        if not (go_backend and baileys_backend):
            return None

        go_ok = go_backend.status in ["ok", "degraded"]
        baileys_ok = baileys_backend.status in ["ok", "degraded"]

        if go_ok and baileys_ok:
            if go_backend.response_time_ms < baileys_backend.response_time_ms:
                return "go"
            else:
                return "baileys"
        return None

    def select_backend(
        self,
        operation: OperationType,
        required_backend: Backend | None = None
    ) -> Backend | None:
        """Select the best backend for the given operation.

        Args:
            operation: Type of operation to route
            required_backend: If specified, only use this backend (or None if unavailable)

        Returns:
            Selected backend ("go" or "baileys") or None if none available
        """
        # If a specific backend is required, check if it's available
        if required_backend:
            if self.health_monitor.is_backend_available(required_backend):
                logger.debug(f"Using required backend: {required_backend}")
                return required_backend
            logger.warning(f"Required backend {required_backend} is not available")
            return None

        # Get routing strategy for this operation
        strategy = self.operation_strategies.get(operation, RoutingStrategy.PREFER_GO)

        # Get health status
        overall_health = self.health_monitor.check_all()
        available_backends = overall_health.available_backends

        # Apply routing strategy
        if strategy == RoutingStrategy.PRIMARY_ONLY:
            primary = overall_health.primary_backend
            return primary if primary != "none" else None

        if strategy == RoutingStrategy.PREFER_GO:
            return self._select_with_preference("go", "baileys", available_backends, operation.value)

        if strategy == RoutingStrategy.PREFER_BAILEYS:
            return self._select_with_preference("baileys", "go", available_backends, operation.value)

        if strategy == RoutingStrategy.ROUND_ROBIN:
            if not available_backends:
                return None
            # Alternate between available backends
            self.round_robin_counter += 1
            idx = self.round_robin_counter % len(available_backends)
            return available_backends[idx]

        if strategy == RoutingStrategy.FASTEST:
            # Try to select fastest
            fastest = self._select_fastest_backend(overall_health)
            if fastest:
                return fastest
            # Fallback to prefer_go logic
            return self._select_with_preference("go", "baileys", available_backends, operation.value)

        return None

    def route_call(
        self,
        operation: OperationType,
        go_func: Callable[..., Any],
        baileys_func: Callable[..., Any] | None = None,
        required_backend: Backend | None = None,
        *args,
        **kwargs
    ) -> tuple[bool, Any]:
        """Route a function call to the appropriate backend.

        Args:
            operation: Type of operation being performed
            go_func: Function to call on Go backend
            baileys_func: Function to call on Baileys backend (if different from go_func)
            required_backend: If specified, only use this backend
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Tuple of (success: bool, result: Any)
        """
        backend = self.select_backend(operation, required_backend)

        if backend is None:
            logger.error(f"No backend available for operation: {operation.value}")
            return False, "No backend available"

        # Execute on selected backend
        try:
            if backend == "go":
                logger.debug(f"Routing {operation.value} to Go backend")
                result = go_func(*args, **kwargs)
                return True, result
            elif backend == "baileys":
                if baileys_func is None:
                    logger.error(f"Baileys function not provided for {operation.value}")
                    return False, "Baileys backend not supported for this operation"

                logger.debug(f"Routing {operation.value} to Baileys backend")
                result = baileys_func(*args, **kwargs)
                return True, result
            else:
                logger.error(f"Unknown backend: {backend}")
                return False, f"Unknown backend: {backend}"

        except Exception as e:
            logger.error(f"Error routing {operation.value} to {backend}: {e}")
            return False, str(e)

    def route_with_fallback(
        self,
        operation: OperationType,
        go_func: Callable[..., Any],
        baileys_func: Callable[..., Any] | None = None,
        *args,
        **kwargs
    ) -> tuple[bool, Any]:
        """Route a call with automatic fallback to other backend if primary fails.

        Args:
            operation: Type of operation being performed
            go_func: Function to call on Go backend
            baileys_func: Function to call on Baileys backend
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Tuple of (success: bool, result: Any)
        """
        # Try primary backend first
        primary_backend = self.select_backend(operation)

        if primary_backend is None:
            return False, "No backend available"

        # Attempt primary backend
        success, result = self.route_call(
            operation, go_func, baileys_func, required_backend=primary_backend, *args, **kwargs
        )

        if success:
            return success, result

        # Primary failed, try fallback
        logger.warning(f"Primary backend {primary_backend} failed, trying fallback")

        # Get available backends
        overall_health = self.health_monitor.check_all()
        fallback_backend = None

        for backend in overall_health.available_backends:
            if backend != primary_backend:
                fallback_backend = backend
                break

        if fallback_backend is None:
            logger.error(f"No fallback backend available for {operation.value}")
            return False, result

        # Attempt fallback
        return self.route_call(
            operation, go_func, baileys_func, required_backend=fallback_backend, *args, **kwargs
        )

    def get_backend_for_operation(self, operation: OperationType) -> Backend | None:
        """Get the backend that would be used for an operation (without executing it).

        Args:
            operation: Type of operation

        Returns:
            Backend that would be selected, or None if none available
        """
        return self.select_backend(operation)

    def is_operation_available(self, operation: OperationType) -> bool:
        """Check if an operation can be performed (i.e., if a backend is available).

        Args:
            operation: Type of operation

        Returns:
            True if operation can be performed
        """
        return self.select_backend(operation) is not None

    def get_routing_info(self) -> dict[str, Any]:
        """Get routing information and statistics.

        Returns:
            Dictionary with routing info
        """
        overall_health = self.health_monitor.check_all()

        return {
            "primary_backend": overall_health.primary_backend,
            "available_backends": overall_health.available_backends,
            "routing_strategies": {
                op.value: strategy.value
                for op, strategy in self.operation_strategies.items()
            },
            "backend_health": {
                "go": {
                    "status": overall_health.go_backend.status,
                    "response_time_ms": overall_health.go_backend.response_time_ms
                } if overall_health.go_backend else None,
                "baileys": {
                    "status": overall_health.baileys_backend.status,
                    "response_time_ms": overall_health.baileys_backend.response_time_ms
                } if overall_health.baileys_backend else None
            }
        }


# Global router instance
_router = None


def get_router() -> Router:
    """Get global router instance (singleton)."""
    global _router
    if _router is None:
        _router = Router()
    return _router
