"""
Unit test fixtures for mocking backends and dependencies.

These fixtures provide mock backends using the responses library
and other mocks for isolated unit testing.
"""

import pytest
import responses
import time
from unittest.mock import Mock, MagicMock
from typing import Dict, List
from dataclasses import dataclass


# Import the routing structures we need to mock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routing import OperationType, RoutingStrategy, Backend


@dataclass
class MockBackendHealth:
    """Mock backend health status"""
    status: str  # "ok", "degraded", "error", "unreachable"
    response_time_ms: float = 100.0
    uptime_seconds: int = 3600
    error_message: str = None


@dataclass
class MockOverallHealth:
    """Mock overall health status"""
    primary_backend: str = "go"
    available_backends: List[str] = None
    go_backend: MockBackendHealth = None
    baileys_backend: MockBackendHealth = None

    def __post_init__(self):
        if self.available_backends is None:
            self.available_backends = []


@pytest.fixture
def mock_go_backend():
    """
    Provides mocked Go backend using responses library.

    Returns a context manager that sets up HTTP mocks for Go backend.
    """
    class GoBackendMock:
        def __init__(self):
            self.base_url = "http://localhost:8080"
            self.health_status = "healthy"
            self.response_delay = 0.0
            self.call_history = []

        def set_health_status(self, status: str):
            """Set health status (healthy/degraded/unhealthy)"""
            self.health_status = status

        def set_response_delay(self, delay_ms: float):
            """Set response delay in milliseconds"""
            self.response_delay = delay_ms / 1000.0

        def inject_error(self, error_type: str):
            """Inject error (timeout/connection_refused/http_500)"""
            self.error_type = error_type

        def setup_health_endpoint(self):
            """Setup health endpoint mock"""
            if self.health_status == "healthy":
                responses.add(
                    responses.GET,
                    f"{self.base_url}/health",
                    json={"status": "ok", "uptime_seconds": 3600},
                    status=200
                )
            elif self.health_status == "degraded":
                responses.add(
                    responses.GET,
                    f"{self.base_url}/health",
                    json={"status": "degraded", "uptime_seconds": 7200},
                    status=200
                )
            elif self.health_status == "unhealthy":
                responses.add(
                    responses.GET,
                    f"{self.base_url}/health",
                    json={"status": "error", "message": "Database connection failed"},
                    status=500
                )

        def get_call_history(self) -> List[Dict]:
            """Get history of all calls made to this backend"""
            return responses.calls

        def reset(self):
            """Reset backend state"""
            self.health_status = "healthy"
            self.response_delay = 0.0
            self.call_history = []

    return GoBackendMock()


@pytest.fixture
def mock_baileys_backend():
    """
    Provides mocked Baileys backend using responses library.

    Returns a context manager that sets up HTTP mocks for Baileys backend.
    """
    class BaileysBackendMock:
        def __init__(self):
            self.base_url = "http://localhost:8081"
            self.health_status = "healthy"
            self.response_delay = 0.0
            self.call_history = []

        def set_health_status(self, status: str):
            """Set health status (healthy/degraded/unhealthy)"""
            self.health_status = status

        def set_response_delay(self, delay_ms: float):
            """Set response delay in milliseconds"""
            self.response_delay = delay_ms / 1000.0

        def inject_error(self, error_type: str):
            """Inject error (timeout/connection_refused/http_500)"""
            self.error_type = error_type

        def setup_health_endpoint(self):
            """Setup health endpoint mock"""
            if self.health_status == "healthy":
                responses.add(
                    responses.GET,
                    f"{self.base_url}/health",
                    json={"status": "ok", "uptime_seconds": 3600},
                    status=200
                )
            elif self.health_status == "degraded":
                responses.add(
                    responses.GET,
                    f"{self.base_url}/health",
                    json={"status": "degraded", "uptime_seconds": 7200},
                    status=200
                )
            elif self.health_status == "unhealthy":
                responses.add(
                    responses.GET,
                    f"{self.base_url}/health",
                    json={"status": "error", "message": "WhatsApp connection lost"},
                    status=500
                )

        def get_call_history(self) -> List[Dict]:
            """Get history of all calls"""
            return responses.calls

        def reset(self):
            """Reset backend state"""
            self.health_status = "healthy"
            self.response_delay = 0.0
            self.call_history = []

    return BaileysBackendMock()


@pytest.fixture
def mock_health_monitor(mock_go_backend, mock_baileys_backend):
    """
    Provides mocked HealthMonitor with controllable backend states.

    Integrates with mock_go_backend and mock_baileys_backend fixtures.
    """
    class MockHealthMonitor:
        def __init__(self):
            self.go_health = MockBackendHealth(status="ok", response_time_ms=100.0)
            self.baileys_health = MockBackendHealth(status="ok", response_time_ms=120.0)

        def set_go_health(self, status: str, response_time_ms: float = 100.0):
            """Set Go backend health status"""
            self.go_health = MockBackendHealth(
                status=status,
                response_time_ms=response_time_ms
            )

        def set_baileys_health(self, status: str, response_time_ms: float = 120.0):
            """Set Baileys backend health status"""
            self.baileys_health = MockBackendHealth(
                status=status,
                response_time_ms=response_time_ms
            )

        def check_all(self) -> MockOverallHealth:
            """Return mock overall health status"""
            available = []

            if self.go_health.status in ["ok", "degraded"]:
                available.append("go")
            if self.baileys_health.status in ["ok", "degraded"]:
                available.append("baileys")

            # Determine primary backend
            primary = "none"
            if "go" in available:
                primary = "go"
            elif "baileys" in available:
                primary = "baileys"

            return MockOverallHealth(
                primary_backend=primary,
                available_backends=available,
                go_backend=self.go_health,
                baileys_backend=self.baileys_health
            )

        def is_backend_available(self, backend: str) -> bool:
            """Check if a specific backend is available"""
            overall = self.check_all()
            return backend in overall.available_backends

    return MockHealthMonitor()


@pytest.fixture
def sample_operations() -> List[Dict]:
    """
    Provides list of operation types with expected backends for testing.

    Returns list of operation type configurations.
    """
    operations = []

    # Message operations (PREFER_GO)
    for op in [OperationType.SEND_MESSAGE, OperationType.SEND_FILE,
               OperationType.SEND_AUDIO, OperationType.MARK_AS_READ]:
        operations.append({
            "type": op,
            "expected_backend": "go",
            "strategy": RoutingStrategy.PREFER_GO
        })

    # History sync operations
    operations.append({
        "type": OperationType.SYNC_FULL_HISTORY,
        "expected_backend": "baileys",
        "strategy": RoutingStrategy.PREFER_BAILEYS
    })

    operations.append({
        "type": OperationType.SYNC_CHAT_HISTORY,
        "expected_backend": "go",
        "strategy": RoutingStrategy.PREFER_GO
    })

    # Community operations (PREFER_GO)
    for op in [OperationType.LIST_COMMUNITIES, OperationType.GET_COMMUNITY_GROUPS,
               OperationType.MARK_COMMUNITY_AS_READ]:
        operations.append({
            "type": op,
            "expected_backend": "go",
            "strategy": RoutingStrategy.PREFER_GO
        })

    # Contact/chat operations (PREFER_GO)
    for op in [OperationType.SEARCH_CONTACTS, OperationType.LIST_CONTACTS,
               OperationType.LIST_CHATS, OperationType.GET_CHAT, OperationType.LIST_MESSAGES]:
        operations.append({
            "type": op,
            "expected_backend": "go",
            "strategy": RoutingStrategy.PREFER_GO
        })

    return operations


@pytest.fixture
def mock_time(monkeypatch):
    """
    Provides frozen time for deterministic time-dependent tests.

    Returns a mock time controller.
    """
    class MockTime:
        def __init__(self):
            self.current_time = 1728745200.0  # Fixed timestamp

        def set_time(self, timestamp: float):
            """Set current time"""
            self.current_time = timestamp

        def advance(self, seconds: float):
            """Advance time by seconds"""
            self.current_time += seconds

        def get_current(self) -> float:
            """Get current time"""
            return self.current_time

    mock = MockTime()

    # Patch time.time() to return mock time
    def mock_time_func():
        return mock.get_current()

    monkeypatch.setattr(time, "time", mock_time_func)

    return mock
