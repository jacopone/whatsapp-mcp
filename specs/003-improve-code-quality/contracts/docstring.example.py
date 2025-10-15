"""Example module demonstrating Google-style docstrings with type hints.

This file serves as a contract template for FR-021 to FR-025 (Documentation).
All public functions must follow this structure.

Enforces: FR-021, FR-022, FR-023, FR-024, FR-025
Success Criteria: SC-013, SC-014, SC-015
"""

from typing import Dict, List, Optional, Any
from unified_mcp.constants import DEFAULT_TIMEOUT


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
    # Implementation would go here
    pass


def send_message(
    chat_jid: str,
    text: str,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """Send text message to WhatsApp chat.

    Args:
        chat_jid: WhatsApp JID of recipient (format: "123456789@s.whatsapp.net").
        text: Message text to send (max 4096 characters).
        timeout: Request timeout in seconds.

    Returns:
        Response dictionary containing:
            - success: bool indicating if send succeeded
            - message_id: str with WhatsApp message ID
            - timestamp: int UNIX timestamp of send

    Raises:
        ValueError: If chat_jid is invalid format or text exceeds length limit.
        TimeoutError: If request exceeds timeout duration.
        ConnectionError: If backend is unreachable.

    Examples:
        Basic message send:

        >>> response = send_message(
        ...     chat_jid="123456789@s.whatsapp.net",
        ...     text="Hello World"
        ... )
        >>> assert response["success"] is True
        >>> assert "message_id" in response

        With custom timeout:

        >>> response = send_message(
        ...     chat_jid="987654321@s.whatsapp.net",
        ...     text="Important message",
        ...     timeout=60
        ... )
    """
    # Implementation would go here
    return {"success": True, "message_id": "ABC123", "timestamp": 1234567890}


class BackendClient:
    """HTTP client for WhatsApp backend bridges.

    Provides methods for sending messages, querying contacts, and managing
    chat state through backend bridge APIs.

    Attributes:
        base_url: Base URL of backend bridge (e.g., "http://localhost:8080").
        timeout: Default timeout for all requests in seconds.
        session: Persistent HTTP session for connection pooling.

    Examples:
        Create client and send message:

        >>> client = BackendClient(base_url="http://localhost:8080")
        >>> response = client.send_message("123@s.whatsapp.net", "Hello")
        >>> assert response["success"] is True

        Query contact list:

        >>> contacts = client.get_contacts(limit=100)
        >>> assert isinstance(contacts, list)
    """

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Initialize backend client.

        Args:
            base_url: Base URL of backend bridge.
            timeout: Default timeout for requests in seconds.

        Raises:
            ValueError: If base_url is not valid HTTP/HTTPS URL.
        """
        self.base_url = base_url
        self.timeout = timeout
        # Session initialization would go here

    def send_message(self, chat_jid: str, text: str) -> Dict[str, Any]:
        """Send text message to chat.

        Args:
            chat_jid: WhatsApp JID of recipient.
            text: Message text to send.

        Returns:
            Response dictionary with success status and message_id.

        Raises:
            ConnectionError: If backend is unreachable.
            TimeoutError: If request times out.

        Examples:
            >>> client = BackendClient("http://localhost:8080")
            >>> result = client.send_message("123@s.whatsapp.net", "Test")
            >>> assert result["success"] is True
        """
        # Implementation would go here
        return {"success": True, "message_id": "MSG123"}

    def get_contacts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve contact list from backend.

        Args:
            limit: Maximum number of contacts to retrieve (1-1000).

        Returns:
            List of contact dictionaries, each containing:
                - jid: WhatsApp JID
                - name: Contact display name
                - phone: Phone number

        Raises:
            ValueError: If limit is out of range.
            ConnectionError: If backend is unreachable.

        Examples:
            >>> client = BackendClient("http://localhost:8080")
            >>> contacts = client.get_contacts(limit=50)
            >>> assert len(contacts) <= 50
            >>> assert all("jid" in c for c in contacts)
        """
        # Implementation would go here
        return []


# =============================================================================
# Docstring Quality Checklist
# =============================================================================
# For every public function/class, verify:
#
# ✅ FR-021: Has docstring (ruff rule D100-D107)
# ✅ FR-022: Follows Google style (ruff --select D)
# ✅ FR-023: Args section documents all parameters
# ✅ FR-024: Returns section describes return value
# ✅ FR-025: Examples section with executable code
#
# ✅ SC-013: All public functions documented
# ✅ SC-014: All follow Google style convention
# ✅ SC-015: All examples pass doctest
#
# Validation commands:
#   ruff check --select D .        # Check docstring completeness
#   pytest --doctest-modules .     # Test all examples
#   mypy --strict .                # Verify type hints match docstrings
