"""Unit tests for backends/health.py - Backend health monitoring.

Tests health check scenarios, status aggregation, and failover logic.
Target: 75%+ coverage of backends/health.py (391 lines)
"""
import time
from unittest.mock import Mock, patch

import requests
import responses

from backends.health import BAILEYS_BRIDGE_URL, GO_BRIDGE_URL, HealthMonitor, get_health_monitor


class TestGoHealthChecks:
    """Test Go backend health check scenarios."""

    @responses.activate
    def test_check_go_health_handles_http_200_ok(self):
        """T067: Test check_go_health handles HTTP 200 OK response correctly."""
        # Setup: Go returns healthy status
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={
                "status": "ok",
                "whatsapp_connected": True,
                "database_ok": True,
                "uptime_seconds": 3600,
                "details": {"version": "1.0.0"}
            },
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check health
        health = monitor.check_go_health()

        # Verify: Healthy status
        assert health.backend == "go"
        assert health.status == "ok"
        assert health.whatsapp_connected is True
        assert health.database_ok is True
        assert health.uptime_seconds == 3600
        assert health.response_time_ms >= 0
        assert monitor.go_failure_count == 0

    def test_check_go_health_handles_timeout(self):
        """T068: Test check_go_health handles connection timeout (5s exceeded)."""
        monitor = HealthMonitor()

        # Mock requests.get to raise Timeout
        with patch('backends.health.requests.get', side_effect=requests.exceptions.Timeout("Connection timeout")):
            # Test: Check health with timeout
            health = monitor.check_go_health(timeout=1)

        # Verify: Unreachable status
        assert health.backend == "go"
        assert health.status == "unreachable"
        assert health.whatsapp_connected is False
        assert health.error_message == "Health check timeout"
        assert monitor.go_failure_count == 1

    def test_check_go_health_handles_connection_refused(self):
        """T069: Test check_go_health handles connection refused (backend down)."""
        monitor = HealthMonitor()

        # Mock requests.get to raise ConnectionError
        with patch('backends.health.requests.get', side_effect=requests.exceptions.ConnectionError("Connection refused")):
            # Test: Check health when connection refused
            health = monitor.check_go_health()

        # Verify: Unreachable status
        assert health.backend == "go"
        assert health.status == "unreachable"
        assert health.whatsapp_connected is False
        assert health.error_message == "Connection refused"
        assert monitor.go_failure_count == 1

    @responses.activate
    def test_check_go_health_handles_http_500_error(self):
        """T070: Test check_go_health handles HTTP 500 error response."""
        # Setup: Go returns HTTP 500
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={"error": "Internal server error"},
            status=500
        )

        monitor = HealthMonitor()

        # Test: Check health with HTTP 500
        health = monitor.check_go_health()

        # Verify: Error status
        assert health.backend == "go"
        assert health.status == "error"
        assert health.whatsapp_connected is False
        assert health.error_message == "HTTP 500"
        assert monitor.go_failure_count == 1

    @responses.activate
    def test_check_go_health_records_response_time_accurately(self):
        """T071: Test check_go_health records response time accurately."""
        # Setup: Go returns healthy with measured response time
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={
                "status": "ok",
                "whatsapp_connected": True,
                "database_ok": True,
                "uptime_seconds": 1800
            },
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check health and measure response time
        start_time = time.time()
        health = monitor.check_go_health()
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify: Response time is reasonable
        assert health.response_time_ms >= 0
        assert health.response_time_ms <= elapsed_ms + 50  # Allow 50ms margin


class TestBaileysHealthChecks:
    """Test Baileys backend health check scenarios."""

    @responses.activate
    def test_check_baileys_health_handles_http_200_ok(self):
        """T072: Test check_baileys_health handles HTTP 200 OK response."""
        # Setup: Baileys returns healthy status
        responses.add(
            responses.GET,
            f"{BAILEYS_BRIDGE_URL}/health",
            json={
                "status": "ok",
                "connected": True,
                "uptime": 7200,
                "details": {"sessions": 1}
            },
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check health
        health = monitor.check_baileys_health()

        # Verify: Healthy status
        assert health.backend == "baileys"
        assert health.status == "ok"
        assert health.whatsapp_connected is True
        assert health.uptime_seconds == 7200
        assert health.response_time_ms >= 0
        assert monitor.baileys_failure_count == 0

    def test_check_baileys_health_handles_timeout(self):
        """T073: Test check_baileys_health handles connection timeout."""
        monitor = HealthMonitor()

        # Mock requests.get to raise Timeout
        with patch('backends.health.requests.get', side_effect=requests.exceptions.Timeout("Connection timeout")):
            # Test: Check health with timeout
            health = monitor.check_baileys_health(timeout=1)

        # Verify: Unreachable status
        assert health.backend == "baileys"
        assert health.status == "unreachable"
        assert health.whatsapp_connected is False
        assert health.error_message == "Health check timeout"
        assert monitor.baileys_failure_count == 1

    def test_check_baileys_health_handles_connection_refused(self):
        """T074: Test check_baileys_health handles connection refused."""
        monitor = HealthMonitor()

        # Mock requests.get to raise ConnectionError
        with patch('backends.health.requests.get', side_effect=requests.exceptions.ConnectionError("Connection refused")):
            # Test: Check health when connection refused
            health = monitor.check_baileys_health()

        # Verify: Unreachable status
        assert health.backend == "baileys"
        assert health.status == "unreachable"
        assert health.whatsapp_connected is False
        assert health.error_message == "Connection refused"
        assert monitor.baileys_failure_count == 1

    @responses.activate
    def test_check_baileys_health_handles_http_500_error(self):
        """T075: Test check_baileys_health handles HTTP 500 error."""
        # Setup: Baileys returns HTTP 500
        responses.add(
            responses.GET,
            f"{BAILEYS_BRIDGE_URL}/health",
            json={"error": "WhatsApp connection lost"},
            status=500
        )

        monitor = HealthMonitor()

        # Test: Check health with HTTP 500
        health = monitor.check_baileys_health()

        # Verify: Error status
        assert health.backend == "baileys"
        assert health.status == "error"
        assert health.whatsapp_connected is False
        assert health.error_message == "HTTP 500"
        assert monitor.baileys_failure_count == 1


class TestHealthAggregation:
    """Test check_all aggregation logic."""

    @responses.activate
    def test_check_all_when_both_backends_healthy(self):
        """T076: Test check_all aggregates health when both backends healthy (overall status="ok")."""
        # Setup: Both backends healthy
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={"status": "ok", "whatsapp_connected": True, "database_ok": True, "uptime_seconds": 3600},
            status=200
        )
        responses.add(
            responses.GET,
            f"{BAILEYS_BRIDGE_URL}/health",
            json={"status": "ok", "connected": True, "uptime": 7200},
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check all backends
        overall = monitor.check_all()

        # Verify: Overall status is "ok"
        assert overall.status == "ok"
        assert overall.primary_backend == "go"
        assert len(overall.available_backends) == 2
        assert "go" in overall.available_backends
        assert "baileys" in overall.available_backends

    def test_check_all_when_only_go_healthy(self):
        """T077: Test check_all aggregates health when only Go healthy (overall status="degraded")."""
        monitor = HealthMonitor()

        # Mock: Go healthy, Baileys down
        def mock_requests_get(url, **kwargs):
            if "8080" in url:  # Go bridge
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "status": "ok",
                    "whatsapp_connected": True,
                    "database_ok": True,
                    "uptime_seconds": 3600
                }
                return mock_response
            else:  # Baileys bridge
                raise requests.exceptions.ConnectionError("Connection refused")

        with patch('backends.health.requests.get', side_effect=mock_requests_get):
            # Test: Check all backends
            overall = monitor.check_all()

        # Verify: Overall status is "degraded"
        assert overall.status == "degraded"
        assert overall.primary_backend == "go"
        assert len(overall.available_backends) == 1
        assert "go" in overall.available_backends

    def test_check_all_when_only_baileys_healthy(self):
        """T078: Test check_all aggregates health when only Baileys healthy (overall status="degraded")."""
        monitor = HealthMonitor()

        # Mock: Go down, Baileys healthy
        def mock_requests_get(url, **kwargs):
            if "8080" in url:  # Go bridge
                raise requests.exceptions.ConnectionError("Connection refused")
            else:  # Baileys bridge
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "status": "ok",
                    "connected": True,
                    "uptime": 7200
                }
                return mock_response

        with patch('backends.health.requests.get', side_effect=mock_requests_get):
            # Test: Check all backends
            overall = monitor.check_all()

        # Verify: Overall status is "degraded", Baileys is primary
        assert overall.status == "degraded"
        assert overall.primary_backend == "baileys"
        assert len(overall.available_backends) == 1
        assert "baileys" in overall.available_backends

    def test_check_all_when_both_backends_down(self):
        """T079: Test check_all aggregates health when both backends down (overall status="error", empty available list)."""
        monitor = HealthMonitor()

        # Mock: Both backends down
        with patch('backends.health.requests.get', side_effect=requests.exceptions.ConnectionError("Connection refused")):
            # Test: Check all backends
            overall = monitor.check_all()

        # Verify: Overall status is "error", no available backends
        assert overall.status == "error"
        assert overall.primary_backend == "none"
        assert len(overall.available_backends) == 0


class TestPrimaryBackendSelection:
    """Test primary backend selection logic."""

    @responses.activate
    def test_primary_backend_prefers_go_when_both_available(self):
        """T080: Test primary backend selection prefers Go over Baileys when both available."""
        # Setup: Both backends available
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={"status": "ok", "whatsapp_connected": True, "database_ok": True, "uptime_seconds": 3600},
            status=200
        )
        responses.add(
            responses.GET,
            f"{BAILEYS_BRIDGE_URL}/health",
            json={"status": "ok", "connected": True, "uptime": 7200},
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check all
        overall = monitor.check_all()

        # Verify: Go is primary
        assert overall.primary_backend == "go"


class TestFailureCounters:
    """Test failure counter management."""

    @responses.activate
    def test_failure_counter_resets_on_successful_health_check(self):
        """T081: Test failure counter resets on successful health check."""
        monitor = HealthMonitor()

        # Setup initial failure
        monitor.go_failure_count = 3

        # Setup: Go returns healthy
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={"status": "ok", "whatsapp_connected": True, "database_ok": True, "uptime_seconds": 3600},
            status=200
        )

        # Test: Successful health check
        health = monitor.check_go_health()

        # Verify: Failure count reset to 0
        assert monitor.go_failure_count == 0
        assert health.status == "ok"

    @responses.activate
    def test_failure_counter_increments_on_failed_health_check(self):
        """T082: Test failure counter increments on failed health check."""
        monitor = HealthMonitor()

        # Setup: Go connection refused
        def connection_error(request):
            raise requests.exceptions.ConnectionError("Connection refused")

        responses.add_callback(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            callback=connection_error
        )

        # Initial state
        assert monitor.go_failure_count == 0

        # Test: First failure
        monitor.check_go_health()
        assert monitor.go_failure_count == 1

        # Test: Second failure
        monitor.check_go_health()
        assert monitor.go_failure_count == 2


class TestWaitForBackend:
    """Test wait_for_backend functionality."""

    @responses.activate
    def test_wait_for_backend_polls_until_available(self):
        """T083: Test wait_for_backend polls until backend becomes available."""
        monitor = HealthMonitor()

        # Setup: First 2 calls fail, 3rd succeeds
        call_count = [0]

        def health_callback(request):
            call_count[0] += 1
            if call_count[0] < 3:
                raise requests.exceptions.ConnectionError("Connection refused")
            return (200, {}, '{"status": "ok", "whatsapp_connected": true, "database_ok": true, "uptime_seconds": 100}')

        responses.add_callback(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            callback=health_callback
        )

        # Test: Wait for backend (should succeed on 3rd try)
        result = monitor.wait_for_backend("go", timeout=10, poll_interval=1)

        # Verify: Success
        assert result is True
        assert call_count[0] >= 3

    @responses.activate
    def test_wait_for_backend_times_out_if_never_available(self):
        """T084: Test wait_for_backend times out if backend never becomes available."""
        monitor = HealthMonitor()

        # Setup: Always fails
        def health_error(request):
            raise requests.exceptions.ConnectionError("Connection refused")

        responses.add_callback(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            callback=health_error
        )

        # Test: Wait for backend (should timeout)
        result = monitor.wait_for_backend("go", timeout=3, poll_interval=1)

        # Verify: Timeout
        assert result is False


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    @responses.activate
    def test_health_check_handles_both_backends_degraded(self):
        """T085: Test health check handles both backends reporting "degraded" simultaneously."""
        # Setup: Both backends degraded
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={"status": "degraded", "whatsapp_connected": True, "database_ok": True, "uptime_seconds": 3600},
            status=200
        )
        responses.add(
            responses.GET,
            f"{BAILEYS_BRIDGE_URL}/health",
            json={"status": "degraded", "connected": True, "uptime": 7200},
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check all backends
        overall = monitor.check_all()

        # Verify: Both still considered available (degraded is usable)
        assert len(overall.available_backends) == 2
        assert "go" in overall.available_backends
        assert "baileys" in overall.available_backends
        assert overall.status == "ok"  # Both degraded still gives overall "ok"

    @responses.activate
    def test_health_check_handles_partial_recovery(self):
        """T086: Test health check handles partial backend recovery (connected but degraded)."""
        # Setup: Go degraded (partial recovery from down state)
        responses.add(
            responses.GET,
            f"{GO_BRIDGE_URL}/health",
            json={"status": "degraded", "whatsapp_connected": False, "database_ok": True, "uptime_seconds": 100},
            status=200
        )

        monitor = HealthMonitor()

        # Test: Check health
        health = monitor.check_go_health()

        # Verify: Degraded is still available
        assert health.status == "degraded"
        assert monitor.is_backend_available("go") is True

    def test_health_check_completes_fast_when_port_closed(self):
        """T087: Test health check completes within 1 second when backend port closed (fast failure)."""
        monitor = HealthMonitor()

        # Mock: Connection refused (port closed)
        with patch('backends.health.requests.get', side_effect=requests.exceptions.ConnectionError("Connection refused")):
            # Test: Check health and measure time
            start_time = time.time()
            health = monitor.check_go_health(timeout=5)
            elapsed = time.time() - start_time

        # Verify: Fast failure (under 1 second)
        assert elapsed < 1.0
        assert health.status == "unreachable"


class TestSingletonInstance:
    """Test global singleton health monitor."""

    def test_get_health_monitor_returns_singleton(self):
        """Test get_health_monitor returns singleton instance."""
        # Test: Get monitor twice
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()

        # Verify: Same instance
        assert monitor1 is monitor2
