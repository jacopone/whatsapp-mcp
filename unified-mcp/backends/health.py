"""Backend health monitoring for the unified WhatsApp MCP.

Monitors the health of both Go/whatsmeow and Baileys bridges,
providing detailed status information and availability tracking.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests

from constants import BAILEYS_BRIDGE_URL, GO_BRIDGE_URL, HEALTH_CHECK_TIMEOUT

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class BackendHealth:
    """Health status for a single backend."""
    backend: str
    status: str  # "ok", "degraded", "error", "unreachable"
    whatsapp_connected: bool
    database_ok: bool
    uptime_seconds: int
    last_check: datetime
    response_time_ms: float
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class OverallHealth:
    """Overall health status for all backends."""
    status: str  # "ok", "degraded", "error"
    primary_backend: str  # "go" or "baileys"
    go_backend: BackendHealth | None
    baileys_backend: BackendHealth | None
    last_check: datetime
    available_backends: list[str]


class HealthMonitor:
    """Monitors the health of both WhatsApp bridges."""

    def __init__(self, check_interval: int = 30, max_retries: int = 3):
        """Initialize health monitor.

        Args:
            check_interval: Seconds between health checks (default: 30)
            max_retries: Number of retries for failed health checks (default: 3)
        """
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.last_go_health: BackendHealth | None = None
        self.last_baileys_health: BackendHealth | None = None
        self.go_failure_count = 0
        self.baileys_failure_count = 0

    def check_go_health(self, timeout: int = HEALTH_CHECK_TIMEOUT) -> BackendHealth:
        """Check health of Go/whatsmeow bridge.

        Args:
            timeout: Request timeout in seconds

        Returns:
            BackendHealth object with current status
        """
        start_time = time.time()

        try:
            response = requests.get(
                f"{GO_BRIDGE_URL}/health",
                timeout=timeout
            )

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                data = response.json()

                health = BackendHealth(
                    backend="go",
                    status=data.get("status", "ok"),
                    whatsapp_connected=data.get("whatsapp_connected", False),
                    database_ok=data.get("database_ok", True),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    details=data.get("details", {})
                )

                self.go_failure_count = 0  # Reset failure count on success
                self.last_go_health = health
                return health

            else:
                # Non-200 status code
                health = BackendHealth(
                    backend="go",
                    status="error",
                    whatsapp_connected=False,
                    database_ok=False,
                    uptime_seconds=0,
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}"
                )
                self.go_failure_count += 1
                return health

        except requests.exceptions.Timeout:
            logger.warning(f"Go bridge health check timed out after {timeout}s")
            self.go_failure_count += 1
            return BackendHealth(
                backend="go",
                status="unreachable",
                whatsapp_connected=False,
                database_ok=False,
                uptime_seconds=0,
                last_check=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Health check timeout"
            )

        except requests.exceptions.ConnectionError:
            logger.warning("Go bridge is unreachable (connection refused)")
            self.go_failure_count += 1
            return BackendHealth(
                backend="go",
                status="unreachable",
                whatsapp_connected=False,
                database_ok=False,
                uptime_seconds=0,
                last_check=datetime.now(),
                response_time_ms=0,
                error_message="Connection refused"
            )

        except Exception as e:
            logger.error(f"Go bridge health check failed: {e}")
            self.go_failure_count += 1
            return BackendHealth(
                backend="go",
                status="error",
                whatsapp_connected=False,
                database_ok=False,
                uptime_seconds=0,
                last_check=datetime.now(),
                response_time_ms=0,
                error_message=str(e)
            )

    def check_baileys_health(self, timeout: int = HEALTH_CHECK_TIMEOUT) -> BackendHealth:
        """Check health of Baileys bridge.

        Args:
            timeout: Request timeout in seconds

        Returns:
            BackendHealth object with current status
        """
        start_time = time.time()

        try:
            response = requests.get(
                f"{BAILEYS_BRIDGE_URL}/health",
                timeout=timeout
            )

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                data = response.json()

                # Baileys health endpoint may have different structure
                health = BackendHealth(
                    backend="baileys",
                    status=data.get("status", "ok"),
                    whatsapp_connected=data.get("whatsapp_connected", data.get("connected", False)),
                    database_ok=data.get("database_ok", True),
                    uptime_seconds=int(data.get("uptime_seconds", data.get("uptime", 0))),
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    details=data.get("details", {})
                )

                self.baileys_failure_count = 0  # Reset failure count on success
                self.last_baileys_health = health
                return health

            else:
                # Non-200 status code
                health = BackendHealth(
                    backend="baileys",
                    status="error",
                    whatsapp_connected=False,
                    database_ok=False,
                    uptime_seconds=0,
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}"
                )
                self.baileys_failure_count += 1
                return health

        except requests.exceptions.Timeout:
            logger.warning(f"Baileys bridge health check timed out after {timeout}s")
            self.baileys_failure_count += 1
            return BackendHealth(
                backend="baileys",
                status="unreachable",
                whatsapp_connected=False,
                database_ok=False,
                uptime_seconds=0,
                last_check=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Health check timeout"
            )

        except requests.exceptions.ConnectionError:
            logger.warning("Baileys bridge is unreachable (connection refused)")
            self.baileys_failure_count += 1
            return BackendHealth(
                backend="baileys",
                status="unreachable",
                whatsapp_connected=False,
                database_ok=False,
                uptime_seconds=0,
                last_check=datetime.now(),
                response_time_ms=0,
                error_message="Connection refused"
            )

        except Exception as e:
            logger.error(f"Baileys bridge health check failed: {e}")
            self.baileys_failure_count += 1
            return BackendHealth(
                backend="baileys",
                status="error",
                whatsapp_connected=False,
                database_ok=False,
                uptime_seconds=0,
                last_check=datetime.now(),
                response_time_ms=0,
                error_message=str(e)
            )

    def check_all(self) -> OverallHealth:
        """Check health of all backends.

        Returns:
            OverallHealth object with combined status
        """
        go_health = self.check_go_health()
        baileys_health = self.check_baileys_health()

        # Determine which backends are available
        available_backends = []
        if go_health.status in ["ok", "degraded"]:
            available_backends.append("go")
        if baileys_health.status in ["ok", "degraded"]:
            available_backends.append("baileys")

        # Determine primary backend (prefer Go if both available)
        primary_backend = "go" if "go" in available_backends else (
            "baileys" if "baileys" in available_backends else "none"
        )

        # Determine overall status
        if len(available_backends) == 2:
            overall_status = "ok"
        elif len(available_backends) == 1:
            overall_status = "degraded"
        else:
            overall_status = "error"

        return OverallHealth(
            status=overall_status,
            primary_backend=primary_backend,
            go_backend=go_health,
            baileys_backend=baileys_health,
            last_check=datetime.now(),
            available_backends=available_backends
        )

    def is_backend_available(self, backend: str) -> bool:
        """Check if a specific backend is available.

        Args:
            backend: "go" or "baileys"

        Returns:
            True if backend is available and healthy
        """
        if backend == "go":
            health = self.check_go_health()
            return health.status in ["ok", "degraded"]
        elif backend == "baileys":
            health = self.check_baileys_health()
            return health.status in ["ok", "degraded"]
        else:
            return False

    def get_preferred_backend(self) -> str | None:
        """Get the preferred backend for routing requests.

        Returns:
            "go" or "baileys" if available, None if both unavailable
        """
        overall = self.check_all()
        return overall.primary_backend if overall.primary_backend != "none" else None

    def wait_for_backend(self, backend: str, timeout: int = 60, poll_interval: int = 5) -> bool:
        """Wait for a backend to become available.

        Args:
            backend: "go" or "baileys"
            timeout: Maximum time to wait in seconds
            poll_interval: Time between checks in seconds

        Returns:
            True if backend became available, False if timeout
        """
        start_time = time.time()

        logger.info(f"Waiting for {backend} backend to become available...")

        while time.time() - start_time < timeout:
            if self.is_backend_available(backend):
                logger.info(f"{backend} backend is now available")
                return True

            time.sleep(poll_interval)

        logger.warning(f"Timeout waiting for {backend} backend to become available")
        return False

    def get_health_summary(self) -> dict[str, Any]:
        """Get a summary of health status for all backends.

        Returns:
            Dictionary with health summary
        """
        overall = self.check_all()

        return {
            "status": overall.status,
            "primary_backend": overall.primary_backend,
            "available_backends": overall.available_backends,
            "backends": {
                "go": {
                    "status": overall.go_backend.status,
                    "whatsapp_connected": overall.go_backend.whatsapp_connected,
                    "response_time_ms": overall.go_backend.response_time_ms,
                    "error": overall.go_backend.error_message
                } if overall.go_backend else None,
                "baileys": {
                    "status": overall.baileys_backend.status,
                    "whatsapp_connected": overall.baileys_backend.whatsapp_connected,
                    "response_time_ms": overall.baileys_backend.response_time_ms,
                    "error": overall.baileys_backend.error_message
                } if overall.baileys_backend else None
            },
            "last_check": overall.last_check.isoformat()
        }


# Global health monitor instance
_health_monitor = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance (singleton)."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
